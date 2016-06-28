
from antevents_upython.mqtt_client import connect, publish, disconnect
from antevents_upython.utils import get_logger
import json

class MQTTWriter:
    __slots__ = ('socket', 'outbound_topic')
    def __init__(self, name, host, port, outbound_topic):
        self.outbound_topic = outbound_topic
        get_logger().info("Connecting to %s:%s" % (host, port))
        self.socket = connect(name, host, port)
        get_logger().info("Connection successful")

    def on_next(self, x):
        data = bytes(json.dumps(x), encoding='utf-8')
        publish(self.socket, self.outbound_topic, data)

    def on_completed(self):
        get_logger().info("Disconnecting from queue")
        disconnect(self.socket)

    def on_error(self, e):
        get_logger().info("Disconnecting from queue due to error")
        disconnect(self.socket)
