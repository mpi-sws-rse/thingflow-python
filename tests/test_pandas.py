"""
Test the adapter to pandas (data analysis library)
"""

import asyncio
import unittest

try:
    import pandas
    PANDAS_AVAILABLE=True
except:
    PANDAS_AVAILABLE = False

from utils import ValueListSensor
from thingflow.base import Scheduler, SensorAsOutputThing

value_stream = [
    20,
    30,
    100,
    120,
    20,
    5,
    2222
]

@unittest.skipUnless(PANDAS_AVAILABLE, "pandas library not installed")
class TestPandas(unittest.TestCase):
    def test_pandas(self):
        s = ValueListSensor(1, value_stream)
        p = SensorAsOutputThing(s)
        import thingflow.adapters.pandas
        import numpy
        w =thingflow.adapters.pandas.PandasSeriesWriter()
        p.connect(w)
        sch = Scheduler(asyncio.get_event_loop())
        sch.schedule_recurring(p)
        sch.run_forever()
        self.assertTrue(w.result is not None, "Result of pandas never set")
        # now we verify each element
        for (i, v) in enumerate(value_stream):
            pv = w.result[i]
            self.assertTrue(isinstance(pv, numpy.int64),
                            "Expecting pandas value '%s' to be numpy.int64, but instead was %s" %
                            (pv, repr(type(pv))))
            self.assertEqual(v, pv,
                             "Pandas value '%s' not equal to original value '%s'" %
                             (repr(pv), repr(v)))
        print("Validate pandas array")

if __name__ == '__main__':
    unittest.main()

        
