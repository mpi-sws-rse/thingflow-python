#!/usr/bin/env python
"""Setup script for antevents distribution. Note that we only
package up the python code. The tests, docs, and examples
are all kept only in the full source repository.
"""

import sys
sys.path.insert(0, 'antevents')
from antevents import __version__

from distutils.core import setup

setup(name='antevents',
      version=__version__,
      description="Event processing library for IOT",
      license="Apache 2.0",
      packages=['antevents', 'antevents.internal', 'antevents.linq',
                'antevents.adapters'],
)
