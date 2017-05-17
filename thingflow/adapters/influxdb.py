import datetime
from influxdb import InfluxDBClient, SeriesHelper

from thingflow.base import OutputThing, InputThing, FatalError

# class BulkUploader(SeriesHelper):
#     def __new__(self, client, msg_format, bulk_size=10):
#         self.client = client
#         self.msg_format = msg_format
#         self.bulk_size = bulk_size 
# 
#     # Meta class stores time series helper configuration.
#     class Meta:
#         # The client should be an instance of InfluxDBClient.
#         client = client
#         # The series name must be a string. Add dependent fields/tags in curly brackets.
#         series_name = msg_format.series_name 
#         # Defines all the fields in this time series.
#         fields = msg_format.fields
#         # Defines all the tags for the series.
#         tags = msg_format.tags 
#         # Defines the number of data points to store prior to writing on the wire.
#         bulk_size = bulk_size
#         # autocommit must be set to True when using bulk_size
#         autocommit = True

class InfluxDBWriter(InputThing):
    """Subscribes to events and writes out to an InfluxDB database"""

    def __init__(self, msg_format, generate_timestamp=True, host="127.0.0.1", port=8086, database="thingflow", 
                 username="root", password="root", 
                 ssl=False, verify_ssl=False, timeout=None, 
                 use_udp=False, udp_port=4444, proxies=None,
                 bulk_size=10):
        self.dbname = database

        self.msg_format = msg_format # a tuple consisting of  {series_name, fields, tags} 
        if not self._validate_msg_format(msg_format):
            raise Exception("Message format should contain series_name (string), fields (string list), and tags (string list)")

        self.generate_timestamp = generate_timestamp 
        self.epoch = datetime.datetime.utcfromtimestamp(0)

        self.client = InfluxDBClient(host=host, port=port, 
                                     username=username, password=password, 
                                     database=database,
                                     ssl=ssl, verify_ssl=verify_ssl, 
                                     timeout=timeout, 
                                     use_udp=use_udp, udp_port=udp_port, 
                                     proxies=proxies)
        self.bulk_size = bulk_size
        print("Message format")
        print(msg_format.series_name)
        print(msg_format.fields)
        print(msg_format.tags)

        # self.client.create_database(database, if_not_exists=True)
        class BulkUploader(SeriesHelper):
            # Meta class stores time series helper configuration.
            class Meta:
                # The client should be an instance of InfluxDBClient.
                client = self.client
                # The series name must be a string. Add dependent fields/tags in curly brackets.
                series_name = msg_format.series_name 
                # Defines all the fields in this time series.
                fields = msg_format.fields
                # Defines all the tags for the series.
                tags = msg_format.tags 
                # Defines the number of data points to store prior to writing on the wire.
                bulk_size = self.bulk_size
                # autocommit must be set to True when using bulk_size
                autocommit = True
                print('In Meta')
                print(series_name, fields, tags)

        # self.bulk_uploader = BulkUploader()

    def _validate_msg_format(self, msg_format):
        return (hasattr(msg_format, 'series_name') and \
                hasattr(msg_format, 'tags') and \
                hasattr(msg_format, 'fields') )

    def on_next(self, msg):
        # write the message on to the database (use the bulk uploader to group writes)
        # assume msg is a dictionary-like object with all fields from msg_format
        flds = { }
        for f in self.msg_format.fields:
            flds[f] = getattr(msg, f)
        tags = { }
        for t in self.msg_format.tags:
            tags[t] = getattr(msg, t)
        if not (self.generate_timestamp) and hasattr(msg, 'ts'):
            time = int(getattr(msg, 'ts') * 1e9)
            json_msg = [ { 'measurement' : self.msg_format.series_name, 
                       'time' : time, 
                       'fields' : flds, 
                       'tags' : tags 
                       } ]
        else:
            json_msg = [ { 'measurement' : self.msg_format.series_name, 
                       'fields' : flds, 
                       'tags' : tags 
                       } ]
        print(json_msg)    
        self.client.write_points(json_msg)
        # self.BulkUploader(msg)


    def on_error(self, e):
        # influx does not have a disconnect. This is because the connection is
        # through a REST API  
        # self.BulkUploader.commit()
        pass

    def on_completed(self):
        # self.BulkUploader.commit()
        pass

    def __str__(self):
        return 'InfluxDB Client(msg=%s)' % self.msg_format.__str__()

class InfluxDBReader(OutputThing):
    def __init__(self, query, host="127.0.0.1", port=8086, database="thingflow", 
                 username="root", password="root", 
                 ssl=False, verify_ssl=False, timeout=None, 
                 use_udp=False, udp_port=4444, proxies=None,
                 bulk_size=10):
        super().__init__()
        self.dbname = database
        self.client = InfluxDBClient(host=host, port=port, 
                                     username=username, password=password, 
                                     database=database,
                                     ssl=ssl, verify_ssl=verify_ssl, 
                                     timeout=timeout, 
                                     use_udp=use_udp, udp_port=udp_port, 
                                     proxies=proxies)
        self.query = query
        self.points = self.client.query(query).get_points()

    def __str__(self):
        return 'InfluxDB[%s]: %s' % (self.dbname, self.query)

    def _observe(self):
        try:
            event = self.points.__next__()
            self._dispatch_next(event)
        except StopIteration:
            self._dispatch_completed()
        except FatalError:
            raise
        except Exception as e:
            self._close()
            self._dispatch_error(e)

    def _close(self):
        pass
