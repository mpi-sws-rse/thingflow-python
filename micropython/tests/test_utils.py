# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
"""These tests are designed to be run on a desktop. You can use
them to validate the system before deploying to 8266. They use stub
sensors.

Test wifi.py and logger.py
"""

import sys
import os
import os.path

try:
    import wifi
    import logger
except ImportError:
    sys.path.append(os.path.abspath('../'))
    import wifi
    import logger


import unittest


class TestLogging(unittest.TestCase):
    def _cleanup(self):
        logger.close_logging()
        for f in ['test.log', 'test.log.1']:
            if os.path.exists(f):
                os.remove(f)

    def setUp(self):
        self._cleanup()

    def tearDown(self):
        self._cleanup()
            
    def test_logging(self):
        self.assertTrue(not os.path.exists('test.log'))
        logger.initialize_logging('test.log', max_len=1024, interactive=True)
        l = logger.get_logger()
        self.assertTrue(os.path.exists('test.log'))
        self.assertTrue(not os.path.exists('test.log.1'))
        l.debug('debug msg')
        l.info('info msg')
        l.warn('warn')
        l.error('error')
        l.info('d'*1024) # force a rollover
        l.info('new file')
        self.assertTrue(os.path.exists('test.log'))
        self.assertTrue(os.path.exists('test.log.1'))

    def test_wifi_connect(self):
        wifi.wifi_connect('foo', 'bar')
        
if __name__ == '__main__':
    unittest.main()
