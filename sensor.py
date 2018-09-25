import os
import RPi.GPIO as GPIO
import time
import datetime
import sys
import base64
import urllib.request, urllib.parse
from yowsup.env import YowsupEnv
from wamedia import SendMediaStack
import mysql.connector
#from array import array
import json
import requests

#inisiasi pin
GPIO.setmode(GPIO.BCM)



TRIG = 23
ECHO = 24

print ("mulai")

GPIO.setup(TRIG,GPIO.OUT)
GPIO.setup(ECHO,GPIO.IN)


#variabel ulang ambil foto
ulang = 1

def credential():
    return "6285559402907","9UcLkHSmh5y/1x1UF72la5S/BhE="

url = "http://andrigunawangh.000webhostapp.com/includes/webservice_noperson.php"
r = requests.get(url)
hh = json.loads(r.text)
loop = len(hh)


while 1:
  ulang = 1 
  GPIO.output(TRIG,True)
  time.sleep(0.00001)
  GPIO.output(TRIG,False)

  while GPIO.input(ECHO)==0:
    pulse_start = time.time()
    
  while GPIO.input(ECHO)==1:
    pulse_end = time.time()
    
  pulse_duration = pulse_end - pulse_start
  distance = pulse_duration * 17150
  distance = round(distance, 2)
  print ("Distance:",distance,"cm")
  time.sleep(0.7)

  if distance<10:
    while ulang<4:
      dt = str(datetime.datetime.now())
      cek = dt[0:4]+dt[5:7]+dt[8:10]+dt[11:13]+dt[14:16]+dt[17:19]+".jpg"
      os.system("fswebcam /home/pi/tugasakhir/"+cek)
      

      time.sleep(5)
      if os.path.exists("/home/pi/tugasakhir/"+cek):
          url = 'http://andrigunawangh.000webhostapp.com/service/service.php'
          foto = open("/home/pi/tugasakhir/"+cek, "rb")
          foto_content = foto.read()
          encoded = base64.b64encode(foto_content)
          data = {'test': encoded, 'nama' : dt[0:4]+dt[5:7]+dt[8:10]+dt[11:13]+dt[14:16]+dt[17:19]}
          encoded_data = bytes(urllib.parse.urlencode(data).encode())
          website = urllib.request.urlopen(url, encoded_data)
         # print (website.read())
          print ("detect")
          for x in hh:
              try:
                  stack = SendMediaStack(credential(),[(x,"/home/pi/tugasakhir/"+cek)])
                  stack.start()
              except:
                pass
      else:
          print ("no foto")
      ulang = ulang+1
      

GPIO.cleanup()
