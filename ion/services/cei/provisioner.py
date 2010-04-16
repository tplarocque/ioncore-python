#!/usr/bin/env python

"""
@file ion/services/cei/provisioner.py
@author Michael Meisinger
@package ion.services.cei service for provisioning operational units (VM instances).
"""

from twisted.python import log
from twisted.internet import defer

from magnet.spawnable import Receiver
from magnet.spawnable import send
from magnet.spawnable import spawn
from magnet.store import Store

store = Store()

receiver = Receiver(__name__)

@defer.inlineCallbacks
def start():
    id = yield spawn(receiver)
    store.put('provisioner', id)


def receive(content, msg):
    print 'in receive ', content, msg

receiver.handle(receive)