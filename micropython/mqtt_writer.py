# Low level comm code originally derived from
# https://github.com/andrewmk/uMQTT. Thus, it is under the GPL license.
# We will replace this with the standard mqtt client for micropython,
# once it become available.

def mtStr(s):
  return bytes([len(s) >> 8, len(s) & 255]) + s.encode('utf-8')

def mtPacket(cmd, variable, payload):
  return bytes([cmd, len(variable) + len(payload)]) + variable + payload

def mtpConnect(name):
  return mtPacket(
           0b00010000,
           mtStr("MQTT") + # protocol name
           b'\x04' +       # protocol level
           b'\x00' +       # connect flag
           b'\xFF\xFF',    # keepalive
           mtStr(name)
  )

def mtpDisconnect():
  return bytes([0b11100000, 0b00000000])

def mtpPub(topic, data):
  return  mtPacket(0b00110001, mtStr(topic), data)

import socket

def connect(name, host, port=1883):
  addr = socket.getaddrinfo(host, port)[0][4]
  s = socket.socket()
  print('Connecting...')
  s.connect(addr)
  s.send(mtpConnect(name))
  resp_header = s.recv(2)
  resp_len = int(resp_header[1])
  s.recv(resp_len)
  return s

# end of code from uMQTT

import json
import utime

class MQTTWriter:
  __slots__ = ('socket', 'topic', 'name', 'host', 'port')
  def __init__(self, name, host, port, topic):
    self.topic = topic
    self.name = name
    self.host = host
    self.port = port
    self._connect()

  def _connect(self):
    print("Connecting to %s:%s" % (self.host, self.port))
    self.socket = connect(self.name, self.host, self.port)
    print("Connection successful")

  def on_next(self, x):
    data = bytes(json.dumps(x), 'utf-8')
    while True:
      try:
        if self.socket==None:
          self._connect()
        self.socket.send(mtpPub(self.topic, data))
        return
      except Exception as e:
        print("Error: %s" % repr(e))
        try:
          self.socket.close()
        except:
          pass
        self.socket = None
        utime.sleep(10)

  def on_completed(self):
    print("mqtt_completed, disconnecting")
    self.socket.send(mtpDisconnect())
    self.socket.close()

  def on_error(self, e):
    print("mqtt on_error: %s, disconnecting" %e)
    self.socket.send(mtpDisconnect())
    self.socket.close()

