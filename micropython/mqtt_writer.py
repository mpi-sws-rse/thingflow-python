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
import binascii

def connect(name, host, port=1883):
  addr = socket.getaddrinfo(host, port)[0][4]
  s = socket.socket()
  print('Connecting...')
  s.connect(addr)
  s.send(mtpConnect(name))
  resp_header = s.recv(2)
  print(binascii.hexlify(resp_header))
  resp_len = int(resp_header[1])
  print("resp_len = %s" % resp_len)
  resp_var = s.recv(resp_len)
  print(binascii.hexlify(resp_var))
  return s

def publish(s, topic, data): 
  s.send(mtpPub(topic, data))

def disconnect(s):
  print('Disconnecting...')
  s.send(mtpDisconnect())
  s.close()

# end of code from uMQTT

import json

class MQTTWriter:
    __slots__ = ('socket', 'outbound_topic')
    def __init__(self, name, host, port, outbound_topic):
        self.outbound_topic = outbound_topic
        print("Connecting to %s:%s" % (host, port))
        self.socket = connect(name, host, port)
        print("Connection successful")

    def on_next(self, x):
        data = bytes(json.dumps(x), encoding='utf-8')
        publish(self.socket, self.outbound_topic, data)

    def on_completed(self):
        print("Disconnecting from queue")
        disconnect(self.socket)

    def on_error(self, e):
        print("Disconnecting from queue due to error")
        disconnect(self.socket)
