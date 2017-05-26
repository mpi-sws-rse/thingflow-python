# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
"""
System-specific configuration variables for tests
Copy this file to config_for_tests.py and make the
changes in your local environment.
"""
import getpass

POSTGRES_DBNAME='iot'
POSTGRES_USER=getpass.getuser()

INFLUXDB_USER='root'
INFLUXDB_PASSWORD=None

#
# Configuration for GE Predix Timeseries API
#
PREDIX_TOKEN=None
PREDIX_ZONE_ID=None
# These URLS are for the west coast data center
PREDIX_INGEST_URL = 'wss://gateway-predix-data-services.run.aws-usw02-pr.ice.predix.io/v1/stream/messages'
PREDIX_QUERY_URL='https://time-series-store-predix.run.aws-usw02-pr.ice.predix.io/v1/datapoints'
