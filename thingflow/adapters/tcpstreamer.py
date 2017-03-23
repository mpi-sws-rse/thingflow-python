# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
"""TODO: This needs to be updated to match the latest base.py!
"""
import asyncio
# log = logging.getLogger(__name__)
# formatter = logging.Formatter("%(asctime)s %(levelname)s " +
#                               "[%(module)s:%(lineno)d] %(message)s")
# log.setLevel(logging.DEBUG)

from thingflow.base import InputThing

clients = {}  # task -> (reader, writer)


class TcpStreamInputThing(InputThing):
    
    def __init__(self, loop, host=None, port=2991):
        self.server = None
        self.task = 0
        self.clients = { }
        self.host = host
        self.port = 2991

        self.loop = loop # TODO REMOVE
        # set up tcp stream
        self.server = loop.run_until_complete(
            asyncio.streams.start_server(self._accept_client,
                                         host, port, loop=loop))

    def __str__(self):
        return "TcpStreamInputThing[{0}, {1}]".format(self.host, self.port)

    def _accept_client(self, client_reader, client_writer):
        """
        This method accepts a new client connection and creates a Task
        to handle this client.  self.clients is updated to keep track
        of the new client.
        """
        print("Accepting new client")
        self.task = self.task + 1
        self.clients[self.task] = (client_reader, client_writer)

    def stop(self):
        """
        Stops the TCP server, i.e. closes the listening socket(s).
        This method runs the loop until the server sockets are closed.
        """
        if self.server is not None:
            self.server.close()
            # TODO: do not have access to loop
            self.loop.run_until_complete(self.server.wait_closed())
            self.server = None

    def on_next(self, msg):
        # send message on tcp stream
        print("tcp: on_next")
        for task, (reader, writer) in self.clients.items():
            try:
                print("tcp: writing to client")
                writer.write(str(msg).encode('utf-8'))
                writer.write('\n'.encode('utf-8')) 
                asyncio.async(writer.drain()) # can this raise exception?
            except ConnectionResetError:
                print("tcp: client disconnected")
                del self.clients[task]
        print("tcp: on_next done")

    def on_error(self, e):
        # close tcp connection
        self.stop()
        print(e)

    def on_completed(self):
        # close tcp connection 
        self.stop()

