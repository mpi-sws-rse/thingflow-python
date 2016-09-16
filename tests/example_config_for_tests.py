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

