#!/usr/bin/env python

"""
@file ion/core/intercept/policy.py
@author Michael Meisinger
@brief Policy checking interceptor
"""

from twisted.internet import defer
from zope.interface import implements, Interface

import ion.util.ionlog
log = ion.util.ionlog.getLogger(__name__)

from ion.core import ioninit
from ion.core.intercept.interceptor import EnvelopeInterceptor

from ion.core.messaging.message_client import MessageInstance

from ion.core.process.cprocess import Invocation

import time

from ion.util.config import Config

from ion.services.coi.datastore_bootstrap.ion_preload_config import OWNED_BY_ID
from ion.services.dm.inventory.association_service import AssociationServiceClient, ASSOCIATION_QUERY_MSG_TYPE
from ion.services.dm.inventory.association_service import IDREF_TYPE
from ion.core.messaging.message_client import MessageClient

CONF = ioninit.config(__name__)

def construct_policy_lists(policydb):
    thedict = {}
    try:
        for policy_entry in policydb:
            role, action, resources = policy_entry
            service, opname = action.split('.', 1)
            assert role in ('ANONYMOUS', 'AUTHENTICATED', 'OWNER', 'ADMIN')

            if role == 'ADMIN':
                role_set = set(['ADMIN'])
            elif role == 'OWNER':
                role_set = set(['OWNER', 'ADMIN'])
            elif role == 'AUTHENTICATED':
                role_set = set(['AUTHENTICATED', 'OWNER', 'ADMIN'])
            else:
                role_set = set(['ANONYMOUS', 'AUTHENTICATED', 'OWNER', 'ADMIN'])

            service_dict = thedict.setdefault(service, {})
            op_dict = service_dict.setdefault(opname, {})
            set_of_roles = op_dict.setdefault('roles', set())
            set_of_roles.update(role_set)
            op_dict['resources'] = resources

    except Exception, ex:
        log.exception('----- POLICY INIT ERROR -----')
        raise ex
    return thedict

policydb_filename = ioninit.adjust_dir(CONF.getValue('policydecisionpointdb'))
policy_dictionary = construct_policy_lists(Config(policydb_filename).getObject())

def construct_user_role_lists(userroledict):
    roledict = {}
    adminlist = []
    for role_entry in userroledict['roles']['ADMIN']:
        subject = role_entry
        role_dict = {'subject': subject, 'ooi_id': None}
        adminlist.append(role_dict);
    roledict['ADMIN'] = adminlist

    dataproviderlist = []
    for role_entry in userroledict['roles']['DATA_PROVIDER']:
        subject = role_entry
        role_dict = {'subject': subject, 'ooi_id': None}
        dataproviderlist.append(role_dict);
    roledict['DATA_PROVIDER'] = dataproviderlist

    attriblist = []
    for attrib_entry_key in userroledict['user-attributes'].keys():
        attrib_dict = {'subject': attrib_entry_key, 'ooi_id': None, 'attributes': userroledict['user-attributes'][attrib_entry_key]}
        attriblist.append(attrib_dict);

    return roledict, attriblist

userroledb_filename = ioninit.adjust_dir(CONF.getValue('userroledb'))
user_role_dict, user_attrib_list = construct_user_role_lists(Config(userroledb_filename).getObject())

def subject_has_role(subject,role):
    for role_entry in user_role_dict[role]:
        if role_entry['subject'] == subject:
            return True
    return False

# Role methods
def user_has_role(ooi_id,role):
    for role_entry in user_role_dict[role]:
        if role_entry['ooi_id'] == ooi_id:
            return True
    return False

def map_ooi_id_to_subject_role(subject,ooi_id,role):
    for role_entry in user_role_dict[role]:
        if role_entry['subject'] == subject:
            role_entry['ooi_id'] = ooi_id
            return

# Role convenience methods
def map_ooi_id_to_subject_admin_role(subject,ooi_id):
    map_ooi_id_to_subject_role(subject,ooi_id,'ADMIN')
            
def subject_has_admin_role(subject):
    return subject_has_role(subject, 'ADMIN')

def user_has_admin_role(ooi_id):
    return user_has_role(ooi_id, 'ADMIN')

def map_ooi_id_to_subject_data_provider_role(subject,ooi_id):
    map_ooi_id_to_subject_role(subject,ooi_id,'DATA_PROVIDER')

def subject_has_data_provider_role(subject):
    return subject_has_role(subject, 'DATA_PROVIDER')

def user_has_data_provider_role(ooi_id):
    return user_has_role(ooi_id, 'DATA_PROVIDER')

# Attribute methods
def get_attribute_value_for_subject(subject,attrib):
    for dict_entry in user_attrib_list:
        if dict_entry['subject'] == subject:
            for attrib_entry_key in dict_entry['attributes'].keys():
                if attrib_entry_key == attrib:
                    return dict_entry['attributes'][attrib]
    return None

def get_attribute_value_for_user(ooi_id,attrib):
    for dict_entry in user_attrib_list:
        if dict_entry['ooi_id'] == ooi_id:
            for attrib_entry_key in dict_entry['attributes'].keys():
                if attrib_entry_key == attrib:
                    return dict_entry['attributes'][attrib]
    return None

def map_ooi_id_to_subject_dispatcher_queue(subject,ooi_id):
    for dict_entry in user_attrib_list:
        if dict_entry['subject'] == subject:
            dict_entry['ooi_id'] = ooi_id
            return

# Attribute convenience methods
def subject_has_attribute(subject, attrib):
    if get_attribute_value_for_subject(subject, attrib) is None:
        return False
    return True

def user_has_attribute(ooi_id, attrib):
    if get_attribute_value_for_user(ooi_id, attrib) is None:
        return False
    return True

def subject_has_dispatcher_queue(subject):
    return subject_has_attribute(subject,'dispatcher-id')

def user_has_dispatcher_queue(ooi_id):
    return user_has_attribute(ooi_id,'dispatcher-id')

def get_dispatcher_queue_for_user(ooi_id):
    return get_attribute_value_for_user(ooi_id,'dispatcher-id')

class PolicyInterceptor(EnvelopeInterceptor):
    def before(self, invocation):
        msg = invocation.content
        return self.is_authorized(msg, invocation)

    def after(self, invocation):
        return invocation
        # msg = invocation.message
        # return self.is_authorized(msg, invocation)

    def is_authorized(self, msg, invocation):
        """
        @brief Policy enforcement method which implements the functionality
            conceptualized as the policy decision point (PDP).
        This method
        will take the specified user id, convert it into a role.  A search
        will then be performed on the global policy_dictionary to determine if
        the user has the appropriate authority to access the specified
        resource via the specified action. A final check is made to determine
        if the user's authentication has expired.
        The following rules are applied to determine authority:
        - If there are no policy tuple entries for service, or no policy
        tuple entries for the specified role, the action is assumed to be allowed.
        - Else, there is a policy tuple for this service:operation.  A check
        is made to ensure the user role is equal to or greater than the
        required role.
        Role precedence from lower to higher is:
            ANONYMOUS, AUTHORIZED, OWNER, ADMIN
        @param msg: message content from invocation
        @param invocation: invocation object passed on interceptor stack.
        @return: invocation object indicating status of authority check
        """

        # Ignore messages that are not of performative 'request'
        if msg.get('performative', None) != 'request':
            return invocation

        # Reject improperly defined messages
        if not 'user-id' in msg:
            log.error("Policy Interceptor: Rejecting improperly defined message missing user-id [%s]." % str(msg))
            invocation.drop(note='Error: no user-id defined in message header!', code=Invocation.CODE_BAD_REQUEST)
            return invocation
        if not 'expiry' in msg:
            log.error("Policy Interceptor: Rejecting improperly defined message missing expiry [%s]." % str(msg))
            invocation.drop(note='Error: no expiry defined in message header!', code=Invocation.CODE_BAD_REQUEST)
            return invocation
        if not 'receiver' in msg:
            log.error("Policy Interceptor: Rejecting improperly defined message missing receiver [%s]." % str(msg))
            invocation.drop(note='Error: no receiver defined in message header!', code=Invocation.CODE_BAD_REQUEST)
            return invocation
        if not 'op'in msg:
            log.error("Policy Interceptor: Rejecting improperly defined message missing op [%s]." % str(msg))
            invocation.drop(note='Error: no op defined in message header!', code=Invocation.CODE_BAD_REQUEST)
            return invocation

        user_id = msg['user-id']
        expirystr = msg['expiry']

        if not type(expirystr) is str:
            log.error("Policy Interceptor: Rejecting improperly defined message with bad expiry [%s]." % str(expirystr))
            invocation.drop(note='Error: expiry improperly defined in message header!', code=Invocation.CODE_BAD_REQUEST)
            return invocation

        try:
            expiry = int(expirystr)
        except ValueError, ex:
            log.error("Policy Interceptor: Rejecting improperly defined message with bad expiry [%s]." % str(expirystr))
            invocation.drop(note='Error: expiry improperly defined in message header!', code=Invocation.CODE_BAD_REQUEST)
            return invocation

        rcvr = msg['receiver']
        service = rcvr.rsplit('.',1)[-1]

        operation = msg['op']

        log.info('Policy Interceptor: Authorization request for service [%s] operation [%s] resource [%s] user_id [%s] expiry [%s]' % (service, operation, '*', user_id, expiry))
        if service in policy_dictionary:
            role = 'ANONYMOUS'
            # TODO figure out mechanism to map user id to role
            if user_id != None and user_id != 'ANONYMOUS':
                if user_has_admin_role(user_id) :
                    log.info('Policy Interceptor: Using ADMIN role.')
                    role = 'ADMIN'
                else:
                    log.info('Policy Interceptor: Using AUTHENTICATED role.')
                    role = 'AUTHENTICATED'
            else:
                log.info('Policy Interceptor: Using ANONYMOUS role.')

            service_list = policy_dictionary[service]
            # TODO figure out how to handle non-wildcard resource ids
            if operation in service_list:
                role_entry = service_list[operation]['roles']
                log.info('Policy Interceptor: Policy tuple [%s]' % str(role_entry))
                if role in role_entry:
                    log.info('Policy Interceptor: Authentication matches')
                else:
                    # See if ownership level entry
                    if 'OWNER' in role_entry:
                        self.check_resource_ownership(invocation, msg, user_id, service_list[operation]['resources'])
                        if invocation.status == Invocation.STATUS_PROCESS:
                            log.info('Policy Interceptor: Authentication matches')
                        else:
                            log.warn('Policy Interceptor: Authentication failed for service [%s] operation [%s] resource [%s] user_id [%s] expiry [%s] for role [OWNER].' % (service, operation, '*', user_id, expiry))
                            return invocation
                    else:
                        log.warn('Policy Interceptor: Authentication failed for service [%s] operation [%s] resource [%s] user_id [%s] expiry [%s] for role [%s]. Returning Not Authorized.' % (service, operation, '*', user_id, expiry, role))
                        invocation.drop(note='Not authorized', code=Invocation.CODE_UNAUTHORIZED)
                        return invocation
        else:
            log.info('Policy Interceptor: service not in policy dictionary.')

        expiry_time = int(expiry)
        if (expiry_time > 0):
            current_time = time.time()

            if current_time > expiry_time:
                log.warn('Policy Interceptor: Current time [%s] exceeds expiry [%s] for service [%s] operation [%s] resource [%s] user_id [%s] . Returning Not Authorized.' % (str(current_time), expiry, service, operation, '*', user_id))
                invocation.drop(note='Authentication expired', code=Invocation.CODE_UNAUTHORIZED)
                return invocation

        log.info('Policy Interceptor: Returning Authorized.')
        return invocation

    def check_resource_ownership(self, invocation, msg, user_id, resources):
        """
        Traverses message structure looking
        for occurrences of field "resource id".
        For each found, association check is made
        to see if user is an owner of the resource.
        """

        self.mc = MessageClient(proc=invocation.process)
        self.asc = AssociationServiceClient()
        
        content = msg.get('content','')
        if isinstance(content, MessageInstance):
            wrapper = content.Message
            repo = content.Repository
            self.check_resource_ownership_traverse_gpbs(invocation, msg, wrapper, repo, user_id, resources)
        else:
            log.error("Policy Interceptor: Rejecting improperly defined message missing MessageInstance [%s]." % str(msg))
            invocation.drop(note='Error: MessageInstance missing from message payload!', code=Invocation.CODE_BAD_REQUEST)

    @defer.inlineCallbacks       
    def check_resource_ownership_traverse_gpbs(self, invocation, msg, wrapper, repo, user_id, resources):
        childLinksSet = wrapper.ChildLinks
        
        if len(childLinksSet) == 0:
            return
            
        for link in wrapper.ChildLinks:
            obj = repo.get_linked_object(link)
            type = obj.ObjectType
            typeId = type.object_id
            if typeId in resources:
                gpbMessage = obj.GPBMessage
                uuid = getattr(gpbMessage,resources[typeId])
                print uuid
                if uuid is None:
                    log.error("Policy Interceptor: Rejecting improperly defined message missing expected uuid [%s]." % str(msg))
                    invocation.drop(note='Error: Uuid missing from message payload!', code=Invocation.CODE_BAD_REQUEST)
                    return
                if uuid == '':
                    log.error("Policy Interceptor: Rejecting improperly defined message missing expected uuid [%s]." % str(msg))
                    invocation.drop(note='Error: Uuid missing from message payload!', code=Invocation.CODE_BAD_REQUEST)
                    return
                
                request = yield self.mc.create_instance(ASSOCIATION_QUERY_MSG_TYPE)

                request.object = request.CreateObject(IDREF_TYPE)
                request.object.key = user_id

                request.predicate = request.CreateObject(IDREF_TYPE)
                request.predicate.key = OWNED_BY_ID

                request.subject = request.CreateObject(IDREF_TYPE)
                request.subject.key = uuid

                # make the request
                result = yield self.asc.association_exists(request)
                if result.result == False:
                    invocation.drop(note='Not authorized', code=Invocation.CODE_UNAUTHORIZED)
                    return

            self.check_resource_ownership_traverse_gpbs(invocation, msg, obj, repo, user_id, resources)

