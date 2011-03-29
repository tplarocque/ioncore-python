#!/usr/bin/env python

"""
@file ion/integration/ais/getDataResourceDetail/getDataResourceDetail.py
@author David Everett
@brief Worker class to get the resource metadata for a given data resource
"""

import ion.util.ionlog
log = ion.util.ionlog.getLogger(__name__)
from twisted.internet import defer

from ion.services.coi.resource_registry_beta.resource_client import ResourceClient, ResourceInstance
#from ion.services.dm.inventory.dataset_controller import DatasetControllerClient
# DHE Temporarily pulling DatasetControllerClient from scaffolding
from ion.integration.ais.findDataResources.resourceStubs import DatasetControllerClient
from ion.integration.ais.getDataResourceDetail.cfdata import cfData

# import GPB type identifiers for AIS
from ion.integration.ais.ais_object_identifiers import AIS_REQUEST_MSG_TYPE, AIS_RESPONSE_MSG_TYPE
from ion.integration.ais.ais_object_identifiers import FIND_DATA_RESOURCES_REQ_MSG_TYPE
from ion.integration.ais.ais_object_identifiers import FIND_DATA_RESOURCES_RSP_MSG_TYPE
from ion.integration.ais.ais_object_identifiers import GET_DATA_RESOURCE_DETAIL_RSP_MSG_TYPE

from ion.core.object import object_utils

class GetDataResourceDetail(object):
    
    def __init__(self, ais):
        log.info('GetDataResourceDetail.__init__()')
        self.ais = ais
        self.rc = ResourceClient()
        self.mc = ais.mc
        self.dscc = DatasetControllerClient()

        
    @defer.inlineCallbacks
    def getDataResourceDetail(self, msg):
        log.debug('getDataResourceDetail Worker Class got GPB: \n' + str(msg))

        rspMsg = yield self.mc.create_instance(AIS_RESPONSE_MSG_TYPE)
        rspMsg.message_parameters_reference.add()
        rspMsg.message_parameters_reference[0] = rspMsg.CreateObject(GET_DATA_RESOURCE_DETAIL_RSP_MSG_TYPE)

        if msg.message_parameters_reference.IsFieldSet('data_resource_id'):
            resID = msg.message_parameters_reference.data_resource_id
        else:
            resID = None
            log.info('DHE: getDataResourceDetail getting test dataset instance.')
            resID = self.ais.getTestDatasetID()
        log.debug('DHE: getDataResourceDetail will get dataset instance: ' + str(resID))
        
        log.debug('DHE: getDataResourceDetail getting resource instance')
        ds = yield self.rc.get_instance(resID)
        #log.debug('DHE: get_instance returned ' + str(ds))

        for atrib in ds.root_group.attributes:
            print 'Root Attribute: %s = %s'  % (str(atrib.name), str(atrib.GetValue()))

        for var in ds.root_group.variables:
            #print 'Root Variable: %s' % str(var.GetStandardName())
            print 'Root Variable: %s' % str(var.name)
            for atrib in var.attributes:
                print "Attribute: %s = %s" % (str(atrib.name), str(atrib.GetValue()))
            print "....Dimensions:"
            for dim in var.shape:
                print "    ....%s (%s)" % (str(dim.name), str(dim.length))

        rspMsg.message_parameters_reference[0].data_resource_id = resID
        # Fill in the rest of the message with the CF metadata
        
        defer.returnValue(rspMsg)

