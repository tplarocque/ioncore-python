#!/usr/bin/env python
"""
@file ion/ops/resources.py
@author David Stuebe

"""


from ion.core import ioninit
from ion.services.coi.resource_registry.resource_client import ResourceClient as RC
from ion.core.object import object_utils
from ion.core.process.process import Process

from ion.services.coi.datastore_bootstrap.ion_preload_config import ROOT_USER_ID, MYOOICI_USER_ID, ANONYMOUS_USER_ID
from ion.services.coi.datastore_bootstrap.ion_preload_config import TYPE_OF_ID, HAS_LIFE_CYCLE_STATE_ID, OWNED_BY_ID, HAS_ROLE_ID, HAS_A_ID, IS_A_ID
from ion.services.coi.datastore_bootstrap.ion_preload_config import SAMPLE_PROFILE_DATASET_ID, SAMPLE_PROFILE_DATA_SOURCE_ID, ADMIN_ROLE_ID, DATA_PROVIDER_ROLE_ID, MARINE_OPERATOR_ROLE_ID, EARLY_ADOPTER_ROLE_ID, AUTHENTICATED_ROLE_ID
from ion.services.coi.datastore_bootstrap.ion_preload_config import RESOURCE_TYPE_TYPE_ID, DATASET_RESOURCE_TYPE_ID, TOPIC_RESOURCE_TYPE_ID, EXCHANGE_POINT_RES_TYPE_ID,EXCHANGE_SPACE_RES_TYPE_ID, PUBLISHER_RES_TYPE_ID, SUBSCRIBER_RES_TYPE_ID, SUBSCRIPTION_RES_TYPE_ID, DATASOURCE_RESOURCE_TYPE_ID, DISPATCHER_RESOURCE_TYPE_ID, DATARESOURCE_SCHEDULE_TYPE_ID, IDENTITY_RESOURCE_TYPE_ID

from ion.services.dm.inventory.dataset_controller import FINDDATASETREQUEST_TYPE, DatasetControllerClient

import ion.util.ionlog
log = ion.util.ionlog.getLogger(__name__)

from twisted.internet import defer

ASSOCIATION_TYPE = object_utils.create_type_identifier(object_id=13, version=1)
PREDICATE_REFERENCE_TYPE = object_utils.create_type_identifier(object_id=25, version=1)
LCS_REFERENCE_TYPE = object_utils.create_type_identifier(object_id=26, version=1)

from ion.services.dm.inventory.association_service import AssociationServiceClient, ASSOCIATION_QUERY_MSG_TYPE, PREDICATE_OBJECT_QUERY_TYPE, IDREF_TYPE, SUBJECT_PREDICATE_QUERY_TYPE
from ion.services.coi.resource_registry.association_client import AssociationClient


# Create a process
resource_process = Process()
resource_process.spawn()

# Create a resource client
rc = RC(resource_process)

# create an association service client
asc = AssociationServiceClient(resource_process)

# create an association client
ac = AssociationClient(resource_process)

# create a dataset controller client
dscc = DatasetControllerClient(resource_process)

# capture the message client
mc = resource_process.message_client

# Set ALL for import *
__all__= ['resource_process','rc','asc','ac','dscc','mc','ROOT_USER_ID', 'MYOOICI_USER_ID', 'ANONYMOUS_USER_ID']
__all__.extend(['TYPE_OF_ID', 'HAS_LIFE_CYCLE_STATE_ID', 'OWNED_BY_ID', 'HAS_ROLE_ID', 'HAS_A_ID', 'IS_A_ID'])
__all__.extend(['SAMPLE_PROFILE_DATASET_ID', 'SAMPLE_PROFILE_DATA_SOURCE_ID', 'ADMIN_ROLE_ID', 'DATA_PROVIDER_ROLE_ID', 'MARINE_OPERATOR_ROLE_ID', 'EARLY_ADOPTER_ROLE_ID', 'AUTHENTICATED_ROLE_ID'])
__all__.extend(['RESOURCE_TYPE_TYPE_ID', 'DATASET_RESOURCE_TYPE_ID', 'TOPIC_RESOURCE_TYPE_ID', 'EXCHANGE_POINT_RES_TYPE_ID', 'EXCHANGE_SPACE_RES_TYPE_ID', 'PUBLISHER_RES_TYPE_ID', 'SUBSCRIBER_RES_TYPE_ID', 'SUBSCRIPTION_RES_TYPE_ID', 'DATASOURCE_RESOURCE_TYPE_ID', 'DISPATCHER_RESOURCE_TYPE_ID', 'DATARESOURCE_SCHEDULE_TYPE_ID', 'IDENTITY_RESOURCE_TYPE_ID'])
__all__.extend(['ASSOCIATION_TYPE','PREDICATE_REFERENCE_TYPE','LCS_REFERENCE_TYPE','ASSOCIATION_QUERY_MSG_TYPE', 'PREDICATE_OBJECT_QUERY_TYPE', 'IDREF_TYPE', 'SUBJECT_PREDICATE_QUERY_TYPE'])
__all__.extend(['find_dataset_keys','find_datasets','pprint_datasets','clear'])





@defer.inlineCallbacks
def _find_dataset_idrefs():
    
    # Creating a new dataset is takes input - it is creating blank resource to be filled by ingestion
    find_request_msg = yield mc.create_instance(FINDDATASETREQUEST_TYPE)

    find_request_msg.only_mine = False
    find_request_msg.by_life_cycle_state = find_request_msg.LifeCycleState.ACTIVE

    # You can send the root of the object or any linked composite part of it.
    find_response_msg = yield dscc.find_dataset_resources(find_request_msg)


    defer.returnValue(find_response_msg.idrefs[:])


@defer.inlineCallbacks
def find_dataset_keys():
    """
    Uses the associations framework to grab all available dataset ids
    @return a list containing the currently available dataset ids as string or unicode objects
    """
    result = []
    idrefs = yield _find_dataset_idrefs()
    
    if len(idrefs) > 0:
        for idref in idrefs:
            result.append(idref.key)
            
        # Add a line return and print each key on its own line encoded in utf-8 format
        log.info('\n\n\t%s' % '\n\t'.join(result).encode('utf-8'))
        
        
    defer.returnValue(result)


@defer.inlineCallbacks
def find_datasets():
    """
    Uses the associations framework to grab all available dataset ids and their resource objects
    @return a dictionary mapping dataset resource keys (ids) to their dataset resource objects
    """
    result = {}
    idrefs = yield _find_dataset_idrefs()
    
    if len(idrefs) > 0:
        for idref in idrefs:
            dataset = yield rc.get_instance(idref)
            result[idref.key] = dataset
                
                
    defer.returnValue(result)


@defer.inlineCallbacks
def pprint_datasets(dataset_dict=None):
    """
    @param dataset_dict: a dictionary mapping dataset resource keys (ids) to their dataset resource objects
                         if the dictionary is None, find_datasets() will be called to populate it
    @return: a defered containing a pretty-formatted output string
    """
    
    if dataset_dict is None:
        dataset_dict = yield find_datasets()
    
    # Add a header
    output = [' ']
    for i in range(182):
        output.append('-')
    output.append('\n |%s|%s|%s|%s|\n ' % ('Resource Key (lifecycle state)'.center(59), 'Dataset Title'.center(60), 'Variable List'.center(30), 'Variable Dimensions'.center(28)))
    for i in range(182):
        output.append('-')
    output.append('\n')
    
    # Iterate over each dataset in the list..
    for key, dataset in dataset_dict.items():
        # Get some info
        title = dataset.root_group.FindAttributeByName('title').GetValue()
        state = dataset.ResourceLifeCycleState
        vrbls = [(var.name, [(dim.name, dim.length) for dim in var.shape]) for var in dataset.root_group.variables]
        
        # Truncate title if its too long
        if len(title) > 58:
            title = '%s...' % title[:55]
        
        # Add the dataset key and title to the output
        key     = '"%s" (%s)' % (key.encode('utf-8'), state.encode('utf-8'))
        title   = '"%s"' % title.encode('utf-8')
        output.append(' %-60s %-60s ' % (key, title))
        for var_name, shape in vrbls:
            
            # Truncate title if its too long
            if len(var_name) > 30:
                var_name = '%s...' % var_name[:27]
                
            # Add each variables name for this dataset to the output
            output.append('%-30s ' % var_name.encode('utf-8'))
            for dim_name, dim_length in shape:
                
                # Add information about the variables dimensions to the output
                output.append('%s(0:%i) ' % (dim_name.encode('utf-8'), dim_length - 1))
                
            # Add necessary whitespace to display the next variable
            output.append('\n%-122s ' % (''))
        
        # Adjust spacing for the next dataset
        del output[-1]
        output.append('\n')
        
        
#    output.insert(0, '\n')
    soutput = ''.join(output)
    del output
    defer.returnValue(soutput)

    
def clear(lines=100):
    """
    Attempts to clear the interactive python console by printing line breaks.
    @param lines: The number of lines to print to the console (default=100)
    """
    for i in range(lines):
        print '\n'

