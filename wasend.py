##from yowsup.stacks                                      import YowStack
##from yowsup.layers                                      import YowLayerEvent
##from yowsup.layers.auth                                 import YowCryptLayer, YowAuthenticationProtocolLayer, AuthError
##from yowsup.layers.coder                                import YowCoderLayer
##from yowsup.layers.network                              import YowNetworkLayer
##from yowsup.layers.protocol_messages                    import YowMessagesProtocolLayer
##from yowsup.layers.stanzaregulator                      import YowStanzaRegulator
##from yowsup.layers.protocol_receipts                    import YowReceiptProtocolLayer
##from yowsup.layers.protocol_acks                        import YowAckProtocolLayer
##from yowsup.layers.logger                               import YowLoggerLayer
##from yowsup.layers                                      import YowParallelLayer
##from yowsup.layers.interface                            import YowInterfaceLayer, ProtocolEntityCallback
##from yowsup.layers.protocol_messages.protocolentities   import TextMessageProtocolEntity
##import threading
##import logging
##logger = logging.getLogger(__name__)

from yowsup.stacks import  YowStackBuilder
from yowsup.layers.auth import AuthError
from yowsup.layers import YowLayerEvent
from yowsup.layers.auth import YowAuthenticationProtocolLayer
from yowsup.layers.network import YowNetworkLayer
from yowsup.layers.interface                           import YowInterfaceLayer, ProtocolEntityCallback
from yowsup.layers.protocol_messages.protocolentities  import TextMessageProtocolEntity
#from yowsup.layers.protocol_presence.protocolentities    import AvailablePresenceProtocolEntity
from yowsup.common.tools import Jid
import threading
import logging
logger = logging.getLogger(__name__)

class SendLayer(YowInterfaceLayer):

    #This message is going to be replaced by the @param message in YowsupSendStack construction
    #i.e. list of (jid, message) tuples
    PROP_MESSAGES = "org.openwhatsapp.yowsup.prop.sendclient.queue"
    
    
    def __init__(self):
        super(SendLayer, self).__init__()
        self.ackQueue = []
        self.lock = threading.Condition()

    #call back function when there is a successful connection to whatsapp server
    @ProtocolEntityCallback("success")
    def onSuccess(self, successProtocolEntity):
        self.lock.acquire()
        for target in self.getProp(self.__class__.PROP_MESSAGES, []):
            #getProp() is trying to retreive the list of (jid, message) tuples, if none exist, use the default []
            phone, message = target
            if '@' in phone:
                messageEntity = TextMessageProtocolEntity(message, to = Jid.normalize(phone))
            elif '-' in phone:
                messageEntity = TextMessageProtocolEntity(message, to = "%s@g.us" % phone)
            else:
                messageEntity = TextMessageProtocolEntity(message, to = "%s@s.whatsapp.net" % phone)
            #append the id of message to ackQueue list
            #which the id of message will be deleted when ack is received.
            self.ackQueue.append(messageEntity.getId())
            self.toLower(messageEntity)
        self.lock.release()
        
    #def presence_available(self, successProtocolEntity):
    #    entity = AvailablePresenceProtocolEntity()
    #   self.toLower(entity)
        
    #after receiving the message from the target number, target number will send a ack to sender(us)
    @ProtocolEntityCallback("ack")
    def onAck(self, entity):
        self.lock.acquire()
        #if the id match the id in ackQueue, then pop the id of the message out
        if entity.getId() in self.ackQueue:
            self.ackQueue.pop(self.ackQueue.index(entity.getId()))
            
        if not len(self.ackQueue):
            self.lock.release()
            #logger.info("Message sent")
            print ("Message sent")
            raise KeyboardInterrupt()

        self.lock.release()

class YowsupSendStack(object):
    def __init__(self, credentials, messages, encryptionEnabled = True):
        """
        :param credentials:
        :param messages: list of (jid, message) tuples
        :param encryptionEnabled:
        :return:
        """
        stackBuilder = YowStackBuilder()

        self.stack = stackBuilder\
            .pushDefaultLayers(encryptionEnabled)\
            .push(SendLayer)\
            .build()

        self.stack.setProp(SendLayer.PROP_MESSAGES, messages)
        self.stack.setProp(YowAuthenticationProtocolLayer.PROP_PASSIVE, True)
        self.stack.setCredentials(credentials)

    def start(self):
        self.stack.broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_CONNECT))
        try:
            self.stack.loop()
        except AuthError as e:
            print("Authentication Error: %s" % e.message)
