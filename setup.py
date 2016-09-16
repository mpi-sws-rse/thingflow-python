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

DESCRIPTION =\
"""
AntEvents is a (Python3) framework for building IOT event processing
dataflows. The goal of this framework is to support the
creation of robust IoT systems from reusable components. These systems must
account for noisy/missing sensor data, distributed computation, and the
need for local (near the data source) processing.

AntEvents is pure Python (3.4 or later). The packaged distribution
(e.g. on PyPi) only includes the core Python code. The source repository at
https://github.com/mpi-sws-rse/antevents-python contains the core Python
code plus the documentation, examples, and tests. There is also a port
of AntEvents for micropython available in the source repo.
"""              

setup(name='antevents',
      version=__version__,
      description="Event Stream processing library for IOT",
      long_description=DESCRIPTION,
      license="Apache 2.0",
      author="MPI-SWS and Data-Ken Research",
      maintainer='Jeff Fischer',
      maintainer_email='jeff+antevents@data-ken.org',
      url='https://github.com/mpi-sws-rse/antevents-python',
      packages=['antevents', 'antevents.internal', 'antevents.linq',
                'antevents.sensors', 'antevents.sensors.rpi',
                'antevents.adapters', 'antevents.adapters.rpi'],
      classifiers = [
          'Development Status :: 4 - Beta',
          'License :: OSI Approved :: Apache Software License',
          'Programming Language :: Python :: 3.4',
          'Programming Language :: Python :: 3.5',
          'Operating System :: OS Independent',
          'Intended Audience :: Developers' ,
      ],
      keywords = ['events', 'iot', 'sensors'],
)
