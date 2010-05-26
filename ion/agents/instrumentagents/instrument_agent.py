#!/usr/bin/env python

import logging
from twisted.internet import defer

from ion.agents.resource_agent import ResourceAgent
from ion.agents.resource_agent import ResourceAgentClient

class InstrumentAgent(ResourceAgent):
    """
    The base class for developing Instrument Agents. This defines
    the interface to use for an instrumen agent.
    """

    def op_get(self, content, headers, msg):
        """
        """

    def op_set(self, content, headers, msg):
        """
        """

    def op_getLifecycleState(self, content, headers, msg):
        """
        """

    def op_setLifecycleState(self, content, headers, msg):
        """
        """

    def op_execute(self, content, headers, msg):
        """
        """

    def op_getStatus(self, content, headers, msg):
        """
        """

    def op_getCapabilities(self, content, headers, msg):
        """
        """

class InstrumentAgentClient(ResourceAgentClient):
    """
    The base class for an Instrument Agent Client. It is a service
    that allows for RPC messaging
    """

    @defer.inlineCallbacks    
    def get(self, valueList):
        """
        Obtain a list of parameter values from the instrument
        @param valueList A list of the values to fetch
        @return A dict of the names and values requested
        """
        assert(isinstance(valueList, list))
        (content, headers, message) = yield self.rpc_send('get', valueList)
        assert(isinstance(content, dict))
        defer.returnValue(content)
    
    @defer.inlineCallbacks
    def set(self, valueDict):
        """
        Set a collection of values on an instrument
        @param valueDict A dict of parameter names and the values they are
            being set to
        @return A dict of the successful set operations that were performed
        @todo Add exceptions for error conditions
        """
        assert(isinstance(valueDict, dict))
        (content, headers, message) = yield self.rpc_send('set', valueDict)
        assert(isinstance(content, dict))
        defer.returnValue(content)
    
    @defer.inlineCallbacks
    def execute(self, commandList):
        """
        Execute the commands in the order of the list. Processing will cease
        when a command fails, but will not roll back.
        @param command_list An ordered list of commands to execute
        @return Dictionary of responses to each execute command
        @todo Alter semantics of this call as needed
        @todo Add exceptions as needed
        """
        result = {}
        assert(isinstance(commandList, list))
        for command in commandList:
            (content, headers, message) = yield self.rpc_send('execute', command)
            result[command] = content
        assert(isinstance(result, dict))
        defer.returnValue(result)
