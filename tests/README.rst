============================
Antevents Tests
============================

This directory contains unit tests for the antlab infrastructure and
adapters. Use the script runtests.sh to run all the tests. If will stop
on the first error it encounters (as signified by a non-zero return code
from the test program).

As much as possible, the tests are standalone and do not require external
dependencies. However, tests of specific adapters will often require some
software to be installed and configured. To support this, we do the following:

 1. Any configuration variables (e.g. usernames, passwords, connect strings)
    go into the file config_for_tests.py. This file is NOT checked into
    git, since it may contain sensitive data. Instead copy the file
    example_config_for_tests.py to config_for_tests.py and adjust it for
    your environment.
2.  Tests with external dependencies use the @unittest.skipUnless decorator
    to check for the dependencies and skip the test if the requirements are
    not met.

