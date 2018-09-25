import os
import sys
#stack
from yowsup.stacks import  YowStackBuilder
from yowsup.layers.auth import AuthError
from yowsup.layers import YowLayerEvent
from yowsup.layers.auth import YowAuthenticationProtocolLayer
from yowsup.layers.network import YowNetworkLayer
from yowsup.env import YowsupEnv
#layer
from yowsup.layers.interface import YowInterfaceLayer, ProtocolEntityCallback
from yowsup.layers.protocol_media.protocolentities import *
from yowsup.layers.protocol_media.mediauploader import MediaUploader



import threading
import logging
logger = logging.getLogger(__name__)

class ImageSent(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)
        
class MediaDiscover(object):
    EXT_IMAGE=['jpg','png']
    EXT_AUDIO=['mp3','wav','aac','wma','ogg','oga']
    EXT_VIDEO=['mp4']

    @staticmethod
    def getMediaType(path):
        for ext in MediaDiscover.EXT_IMAGE:
            if path.endswith(ext):
                return "image"
        for ext in MediaDiscover.EXT_VIDEO:
            if path.endswith(ext):
                return "video"
        for ext in MediaDiscover.EXT_AUDIO:
            if path.endswith(ext):
                return "audio"    
        return None                
 
class SendMediaLayer(YowInterfaceLayer):
    PROP_MESSAGES = 'org.openwhatsapp.yowsup.prop.sendclient.queue'  # list of (jid, path) tuples

    def __init__(self):
        super(SendMediaLayer,self).__init__()
        self.MEDIA_TYPE=None
        self.ackQueue=[]
        self.lock = threading.Condition()

    def disconnect(self,result):
        self.broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_DISCONNECT))
        raise ImageSent(result+" "+self.MEDIA_TYPE)

    @ProtocolEntityCallback('success')
    def onSuccess(self,entity):
        self.main()

    @ProtocolEntityCallback('ack')
    def onAck(self,entity):
        if entity.getId() in self.ackQueue:
            self.ackQueue.pop(self.ackQueue.index(entity.getId()))
        if not len(self.ackQueue):
            self.disconnect("MEDIA SENT")

    def onRequestUploadResult(self,jid,filePath,resultRequestUploadIqProtocolEntity,requestUploadIqProtocolEntity):
        if resultRequestUploadIqProtocolEntity.isDuplicate():
            if self.MEDIA_TYPE=="image":
                self.doSendImage(filePath,resultRequestUploadIqProtocolEntity.getUrl(),jid,resultRequestUploadIqProtocolEntity.getIp())
            elif self.MEDIA_TYPE=="video":
                self.doSendVideo(filePath,resultRequestUploadIqProtocolEntity.getUrl(),jid,resultRequestUploadIqProtocolEntity.getIp())
            elif self.MEDIA_TYPE=="audio":
                self.doSendAudio(filePath,resultRequestUploadIqProtocolEntity.getUrl(),jid,resultRequestUploadIqProtocolEntity.getIp())
        else:
            mediaUploader=MediaUploader(jid,self.getOwnJid(),filePath,resultRequestUploadIqProtocolEntity.getUrl(),resultRequestUploadIqProtocolEntity.getResumeOffset(),self.onUploadSuccess,self.onUploadError,self.onUploadProgress,async=False)
            mediaUploader.start()

    def onRequestUploadError(self,jid,path,errorRequestUploadIqProtocolEntity,requestUploadIqProtocolEntity):
        logger.error("Request upload for file %s for %s failed" % (path,jid))
        self.disconnect("ERROR REQUEST")

    def onUploadSuccess(self,filePath,jid,url):
        if self.MEDIA_TYPE=="image":
            self.doSendImage(filePath,url,jid)
        elif self.MEDIA_TYPE=="video":
            self.doSendVideo(filePath,url,jid)
        elif self.MEDIA_TYPE=="audio":
            self.doSendAudio(filePath,url,jid)

    def onUploadError(self,filePath,jid,url):
        logger.error("Upload file %s to %s for %s failed" % (filepath,url,jid))
        self.disconnect("ERROR UPLOAD")

    def onUploadProgress(self,filePath,jid,url,progress):
        print(progress)

    def doSendImage(self,filePath,url,to,ip=None):
        entity=ImageDownloadableMediaMessageProtocolEntity.fromFilePath(filePath,url,ip,to)
        self.toLower(entity)

    def doSendVideo(self,filePath,url,to,ip=None):
        entity=DownloadableMediaMessageProtocolEntity.fromFilePath(filePath,url,"video",ip,to)
        self.toLower(entity)

    def doSendAudio(self,filePath,url,to,ip=None):
        entity=DownloadableMediaMessageProtocolEntity.fromFilePath(filePath,url,"audio",ip,to)
        self.toLower(entity)

    def main(self):
        for target in self.getProp(self.__class__.PROP_MESSAGES,[]):
            jid,path=target
            #print caption
            jid='%s@s.whatsapp.net' % jid
            self.MEDIA_TYPE=MediaDiscover.getMediaType(path)
            if self.MEDIA_TYPE is None:
                self.disconnect("ERROR MEDIA")
            entity = None
            if self.MEDIA_TYPE=="image":
                entity=RequestUploadIqProtocolEntity(RequestUploadIqProtocolEntity.MEDIA_TYPE_IMAGE,filePath=path)
            elif self.MEDIA_TYPE=="video":
                entity=RequestUploadIqProtocolEntity(RequestUploadIqProtocolEntity.MEDIA_TYPE_VIDEO,filePath=path)
            elif self.MEDIA_TYPE=="audio":
                entity=RequestUploadIqProtocolEntity(RequestUploadIqProtocolEntity.MEDIA_TYPE_AUDIO,filePath=path)
            successFn=lambda successEntity, originalEntity: self.onRequestUploadResult(jid,path,successEntity,originalEntity)
            errorFn=lambda errorEntity,originalEntity: self.onRequestUploadError(jid,path,errorEntity,originalEntity)
            self._sendIq(entity,successFn,errorFn)

class SendMediaStack(object):
    def __init__(self, credentials, messages, encryptionEnabled = True):
        stackBuilder = YowStackBuilder()
        self.stack = stackBuilder\
            .pushDefaultLayers(encryptionEnabled)\
            .push(SendMediaLayer)\
            .build()
        self.stack.setProp(SendMediaLayer.PROP_MESSAGES,messages)
        self.stack.setProp(YowAuthenticationProtocolLayer.PROP_PASSIVE,True)
        self.stack.setCredentials(credentials)
        
    def start(self):
        self.stack.broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_CONNECT))
        try:
            self.stack.loop()
        except AuthError as e:
            print("Authentication Error: %s" % e.message)
