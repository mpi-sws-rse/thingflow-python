"""These tests are designed to be run on a desktop. You can use
them to validate the system before deploying to 8266. They use stub
sensors.

Test the upython_utils.py module.
"""

import sys
import os
import os.path

try:
    import upython_utils
except ImportError:
    sys.path.append(os.path.abspath('../'))
    import upython_utils

import unittest

from upython_utils import *

class TestLogging(unittest.TestCase):
    def _cleanup(self):
        close_logging()
        for f in ['test.log', 'test.log.1']:
            if os.path.exists(f):
                os.remove(f)

    def setUp(self):
        self._cleanup()

    def tearDown(self):
        self._cleanup()
            
    def test_logging(self):
        self.assertTrue(not os.path.exists('test.log'))
        initialize_logging('test.log', max_len=1024, interactive=True)
        l = get_logger()
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
        initialize_logging('test.log', max_len=1024, interactive=True)
        wifi_connect('foo', 'bar')
        
if __name__ == '__main__':
    unittest.main()
