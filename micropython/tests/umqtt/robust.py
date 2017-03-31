"""Fake mqtt interface - this simulates the api provided
by micropython. We use paho.mqtt to talk to the broker.
"""
import paho.mqtt.client

class MQTTClient:
    def __init__(self, name, host, port):
        self.client = paho.mqtt.client.Client(name)
        self.host = host
        self.port = port

    def connect(self):
        self.client.connect(self.host, self.port)
        self.client.loop_start()


    def disconnect(self):
        self.client.disconnect()
        self.client.loop_stop(force=False)

    def publish(self, topic, data):
        topic = str(topic, encoding='utf-8') # paho wants a string
        print("publishing %s on %s" % (repr(data), repr(topic)))
        self.client.publish(topic, data)

