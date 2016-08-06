#!/bin/bash
# Really simple test runner.
# Runs a bunch of python unit tests as standalone programs
# and collects the results.

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

# Counts of each test result type
OK=0
SKIPPED=0
FAILED=0
ERROR=0

# Run a single test and update the counts. Takes one argument: the test name.
# A .py will be appended to get the python filename. The standard output
# goes into $TEST.out and the standard error to $TEST.err. These are not
# kept unless the test fails.
function runtest {
    TEST=$1
    echo -n "Running $TEST"
    $PYTHON $TEST.py >$TEST.out 2>$TEST.err
    rc=$?
    if [[ "$rc" == 0 ]]; then
	# got a success. Now check whether skipped.
	tail -1 $TEST.err | grep -q 'OK (skipped'
	skiprc=$?
	if [[ "$skiprc" == "0" ]]; then
	    echo "  SKIPPED"
	    SKIPPED=$((SKIPPED+1))
	    rm $TEST.err $TEST.out
        else
	    tail -1 $TEST.err | grep -q 'OK'
	    okrc=$?
	    if [[ "$okrc" == "0" ]]; then
		echo "  OK"
		OK=$((OK+1))
		rm $TEST.err $TEST.out
	    else
		# did not find the OK
		echo "  UNKNOWN!"
		ERROR=$((ERROR+1))
	    fi # okrc
	fi # skiprc
    else # non-zero return code
	tail -l $TEST.err | grep -q 'FAILED'
	failrc=$?
	if [[ "$failrc" == "0" ]]; then
	    echo "  FAILED"
	    FAILED=$((FAILED+1))
	else
	    echo "  ERROR"
	    ERROR=$((ERROR+1))
	fi # failrc
    fi # rc
}    
    
###########################
# Run the tests
###########################
rm -f *.err *.out
echo ">>>>>>>>>>>>>>>>>>>> Starting Tests"

runtest test_base
runtest test_iterable_as_publisher
runtest test_external_event_stream
runtest test_multiple_pubtopics
runtest test_linq
runtest test_transducer
runtest test_scheduler_cancel
runtest test_fatal_error_handling
runtest test_fatal_error_in_private_loop
runtest test_blocking_publisher
runtest test_solar_heater_scenario
runtest test_timeout
runtest test_blocking_subscriber
runtest test_postgres_adapters
runtest test_mqtt
runtest test_csv_adapters


echo ">>>>>>>>>>>>>>>>>>>> Finished Tests"
echo "$OK Tests successful."
echo "$SKIPPED Tests skipped."
echo "$FAILED Tests failed."
echo "$ERROR Tests had errors."
exit $((FAILED + ERROR))
