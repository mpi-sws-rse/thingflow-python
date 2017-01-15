# Writer interface over umqtt API.

from umqtt.robust import MQTTClient
import json

class MQTTWriter:
  __slots__ = ('host', 'port', 'topic', 'client')
  def __init__(self, name, host, port, topic):
    self.topic = topic
    self.host = host
    self.port = port
    self.client = MQTTClient(name, host, port)
    self._connect()

  def _connect(self):
    print("Connecting to %s:%s" % (self.host, self.port))
    self.client.connect()
    print("Connection successful")

  def on_next(self, x):
    data = bytes(json.dumps(x), 'utf-8')
    self.client.publish(bytes(self.topic, 'utf-8'), data)

  def on_completed(self):
    print("mqtt_completed, disconnecting")
    self.client.disconnect()

  def on_error(self, e):
    print("mqtt on_error: %s, disconnecting" %e)
    self.client.disconnect()

