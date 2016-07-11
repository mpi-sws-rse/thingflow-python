#!/bin/bash
# really simple test runner

###########################
# Environment setup
###########################
# Try to guess which python points to python 3
if [[ "`which python3`" == "" ]]; then
    PYTHON=`which python`
else
    PYTHON=`which python3`
fi
if [[ "$PYTHON" == "" ]]; then
    echo "Could not find python!"
    exit 1
fi
# verify that it is a python3
$PYTHON -c "import sys; sys.exit(0 if sys.version.startswith('3.') else 1)"
if [[ "$?" == 1 ]]; then
   echo "Wrong version of python, need python 3.x, got `$PYTHON --version`"
   exit 1
fi
echo "Using python at $PYTHON"
# set python path if necessary
if [[ "$PYTHONPATH" == "" ]]; then
    export PYTHONPATH=`cd ..; pwd`
    echo "Set PYTHONPATH to $PYTHONPATH"
fi

set -e # stop on first error
set -v # echo everything being done

###########################
# Run the tests
###########################
$PYTHON test_base.py
$PYTHON test_external_event_stream.py
$PYTHON test_multiple_pubtopics.py
$PYTHON test_linq.py
$PYTHON test_transducer.py
$PYTHON test_scheduler_cancel.py
$PYTHON test_fatal_error_handling.py
$PYTHON test_fatal_error_in_private_loop.py
$PYTHON test_blocking_publisher.py
$PYTHON test_solar_heater_scenario.py
$PYTHON test_timeout.py
$PYTHON test_blocking_subscriber.py
$PYTHON test_postgres_adapters.py
$PYTHON test_mqtt.py
$PYTHON test_csv_adapters.py

echo ">> tests successful."
