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
        w =thingflow.adapters.pandas.PandasSeriesWriter()
        p.connect(w)
        sch = Scheduler(asyncio.get_event_loop())
        sch.schedule_recurring(p, 0.25)
        sch.run_forever()
        self.assertTrue(w.result is not None, "Result of pandas never set")


if __name__ == '__main__':
    unittest.main()

        
