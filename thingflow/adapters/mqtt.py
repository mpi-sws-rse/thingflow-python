# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
import time
from collections import namedtuple

try:
    import paho.mqtt.client as paho
except ImportError:
    print("could not import paho.mqtt.client")

import ssl

from thingflow.base import InputThing, OutputThing, EventLoopOutputThingMixin


MQTTEvent = namedtuple('MQTTEvent', ['timestamp', 'state', 'mid', 'topic', 'payload', 'qos', 'dup', 'retain' ])


import random
random.seed()
import datetime

class MockMQTTClient(object):
    def __init__(self, client_id=""):
        self.userdata = None
        self.client_id = client_id
        self.on_message = None
        self.on_connect = None
        self.on_publish = None

    def connect(self, host, port=1883):
        if self.on_connect:
            self.on_connect(self, self.userdata, None, 0)
        return 0

    def subscribe(self, topics):
        pass

    def publish(self, topic, payload, qos, retain=False):
        if self.on_publish:
            self.on_publish(self, self.userdata, 0)

    def username_pw_set(self, username, password=""):
        pass

    def loop(self, timeout=1.0, max_packets=1):
        s = random.randint(1, max_packets)
        for i in range(0, s):
            msg = MQTTEvent(datetime.datetime.now(), 0, i, 'bogus/bogus', 'xxx', 0, False, False)
            if self.on_message:
                self.on_message(self, self.userdata, msg)
        time.sleep(timeout)
        return 0

    def disconnect(self):
        pass

class MQTTWriter(InputThing):
    """Subscribes to internal events and pushes them out to MQTT.
    The topics parameter is a list of (topic, qos) pairs.

    Events should be serialized before passing them to the writer.
    """
    def __init__(self, host, port=1883, client_id="", client_username="", client_password=None, server_tls=False, server_cert=None, topics=[], mock_class=None):
        self.host = host
        self.port = port
        self.client_id = client_id
        self.client_username = client_id
        self.client_password = client_password
        self.topics = topics

        self.server_tls =  server_tls
        self.server_cert = server_cert

        if mock_class:
            self.client = MockMQTTClient(self.client_id)
        else:
            self.client = paho.Client(self.client_id)

        if self.client_username:
            self.client.username_pw_set(self.client_username, password=self.client_password)

        self._connect()
 
    def _connect(self):
        if self.server_tls:
            raise Exception("TBD")
            print(self.client.tls_set(self.server_tls.server_cert, cert_reqs=ssl.CERT_OPTIONAL))
            print(self.client.connect(self.host, self.port))
        else:
            self.client.connect(self.host, self.port) 
            self.client.subscribe(self.topics)
   
        def on_connect(client, userdata, flags, rc):
            print("Connected with result code "+str(rc))
        self.client.on_connect = on_connect

        def on_publish(client, userdata, mid):
            print("Successfully published mid %d" % mid)
        self.client.on_publish = on_publish


    def on_next(self, msg):
        """Note that the message is passed directly to paho.mqtt.client. As such,
        it must be a string, a bytearray, an int, a float or None. Usually, you would
        use something like to_json (in thingflow.filters.json) to do the
        serialization of events.
        """
        # publish the message to the topics
        retain = msg.retain if hasattr(msg, 'retain') else False
        for (topic, qos) in self.topics:
            self.client.publish(topic, msg, qos, retain) 

    def on_error(self, e):
        self.client.disconnect()
 
    def on_completed(self):
        self.client.disconnect()

    def __str__(self):
        return 'MQTTWriter(%s)' % ', '.join([topic for (topic,qos) in self.topics])
        

class MQTTReader(OutputThing, EventLoopOutputThingMixin):
    """An reader that creates a stream from an MQTT broker. Initialize the
       reader with a list of topics to subscribe to. The topics parameter
       is a list of (topic, qos) pairs.

       Pre-requisites: An MQTT broker (on host:port) --- tested with mosquitto
                   The paho.mqtt python client for mqtt (pip install paho-mqtt)
    """
    def __init__(self, host, port=1883, client_id="", client_username="", client_password=None, server_tls=False, server_cert=None, topics=[], mock_class=None):
        super().__init__()
        self.stop_requested = False

        self.host = host
        self.port = port
        self.client_id = client_id
        self.client_username = client_id
        self.client_password = client_password
        self.topics = topics

        self.server_tls =  server_tls
        self.server_cert = server_cert

        if mock_class:
            self.client = MockMQTTClient(self.client_id)
        else:
            self.client = paho.Client(self.client_id)

        if self.client_username:
            self.client.username_pw_set(self.client_username, password=self.client_password)

        self._connect()
 
        def on_message(client, userdata, msg):
            m =  MQTTEvent(msg.timestamp, msg.state, msg.mid, msg.topic, msg.payload, msg.qos, msg.dup, msg.retain)
            self._dispatch_next(m)
        self.client.on_message = on_message
   
    def _connect(self):
        if self.server_tls:
            raise Exception("TBD")
            print(self.client.tls_set(self.server_tls.server_cert, cert_reqs=ssl.CERT_OPTIONAL))
            print(self.client.connect(self.host, self.port))
        else:
            self.client.connect(self.host, self.port) 
   
        def on_connect(client, userdata, flags, rc):
            print("Connected with result code "+str(rc))

            # Subscribing in on_connect() means that if we lose the connection and
            # reconnect then subscriptions will be renewed.
            client.subscribe(self.topics)
        self.client.on_connect = on_connect

        
    def _observe_event_loop(self):
        print("starting event loop")
        while True:
            if self.stop_requested:
                break
            result = self.client.loop(1)
            if result != 0:
                self._connect()
        self.stop_requested = False
        self.client.disconnect()
        print("Stopped private event loop")
            
    def _stop_loop(self):
        self.stop_requested = True
        print("requesting stop")

    def __str__(self):
        return 'MQTTReader(%s)' % ', '.join([topic for (topic,qos) in self.topics])
