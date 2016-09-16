#!/usr/bin/env python
# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
"""Setup script for antevents distribution. Note that we only
package up the python code. The tests, docs, and examples
are all kept only in the full source repository.
"""

import sys
sys.path.insert(0, 'antevents')
from antevents import __version__

#We try setuptools first (which has more features), and
# fallback to distutils if setuptools was not installed.
try:
    from setuptools import setup
except ImportError:
    print("Did not find setuptools, using distutils instead")
    from distutils.core import setup
    

setup(name='antevents',
      version=__version__,
      description="Event Stream processing library for IOT",
      license="Apache 2.0",
      url='https://github.com/mpi-sws-rse/antevents-python',
      packages=['antevents', 'antevents.internal', 'antevents.linq',
                'antevents.sensors', 'antevents.sensors.rpi',
                'antevents.adapters', 'antevents.adapters.rpi'],
      classifiers = [
          'Development Status :: 4 - Beta',
          'License :: OSI Approved :: Apache Software License',
          'Programming Language :: Python :: 3.4',
          'Programming Language :: Python :: 3.5',
          'Intended Audience :: Developers',
      ],
)
