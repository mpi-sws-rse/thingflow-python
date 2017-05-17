#!/bin/bash
# Really simple test runner.
# Runs a bunch of python unit tests as standalone programs
# and collects the results.

###########################
# Test definitions
###########################
# We define the test names here. Given a name NAME, the python file should be NAME.py.
# The tests will be run in order, unless a subset is provided on the command line.
TESTS="test_base test_iterable_as_output_thing test_external_event_stream test_multiple_output_ports test_linq test_transducer test_scheduler_cancel test_fatal_error_handling test_fatal_error_in_private_loop test_blocking_output_thing test_solar_heater_scenario test_timeout test_blocking_input_thing test_postgres_adapters test_mqtt test_mqtt_async test_csv_adapters test_functional_api test_tracing test_pandas test_rpi_adapters test_influxdb"



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

# Escape codes for color text
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m' # yellow
NC='\033[0m' # No Color

# Run a single test and update the counts. Takes one argument: the test name.
# A .py will be appended to get the python filename. The standard output
# goes into $TEST.out and the standard error to $TEST.err. These are not
# kept unless the test fails.
function runtest {
    TEST=$1
    echo -n "Running $TEST"
    $PYTHON ${TEST}.py >${TEST}.out 2>${TEST}.err
    rc=$?
    if [[ "$rc" == 0 ]]; then
	# got a success. Now check whether skipped.
	tail -1 $TEST.err | grep -q 'OK (skipped'
	skiprc=$?
	if [[ "$skiprc" == "0" ]]; then
	    echo -e "  ${YELLOW}SKIPPED${NC}"
	    SKIPPED=$((SKIPPED+1))
	    rm $TEST.err $TEST.out
        else
	    tail -1 $TEST.err | grep -q 'OK'
	    okrc=$?
	    if [[ "$okrc" == "0" ]]; then
		echo -e "  ${GREEN}OK${NC}"
		OK=$((OK+1))
		rm $TEST.err $TEST.out
	    else
		# did not find the OK
		echo -e "  ${RED}UNKNOWN!${NC}"
		ERROR=$((ERROR+1))
	    fi # okrc
	fi # skiprc
    else # non-zero return code
	tail -1 $TEST.err | grep -q 'FAILED'
	failrc=$?
	if [[ "$failrc" == "0" ]]; then
	    echo -e "  ${RED}FAILED${NC}"
	    FAILED=$((FAILED+1))
	else
	    echo -e "  ${RED}ERROR${NC}"
	    ERROR=$((ERROR+1))
	fi # failrc
    fi # rc
}    


###########################
# validate command line arguments
###########################
if [[ "$#" == "0" ]]; then
   TESTS_TO_RUN=$TESTS
else
    ARGS=${@:1}
    for tst in $ARGS; do
	found=0
	for chktst in $TESTS; do
	    if [[ "$chktst" == "$tst" ]]; then
		found=1
		break
	    fi
	done
	if [[ $found != 1 ]]; then
	    echo -e "${RED}ERROR: $tst is not a known test.${NC}"
	    echo "Valid tests are: $TESTS"
	    exit 1
	fi
    done
    TESTS_TO_RUN=$ARGS
fi


###########################
# Run the tests
###########################
rm -f *.err *.out

echo ">>>>>>>>>>>>>>>>>>>> Starting Tests"


for tst in $TESTS_TO_RUN; do
    runtest ${tst}
done

echo ">>>>>>>>>>>>>>>>>>>> Finished Tests"
if [[ "$OK" == "0" ]]; then
   echo -e "${RED}0 Tests successful.${NC}"
else
    echo -e "${GREEN}$OK Tests successful.${NC}"
fi
if [[ "$SKIPPED" == "0" ]]; then
    echo -e "${GREEN}0 Tests skipped.${NC}"
else
    echo -e "${YELLOW}$SKIPPED Tests skipped.${NC}"
fi    
if [[ "$FAILED" == "0" ]]; then
    echo -e "${GREEN}0 Tests failed.${NC}"
else
    echo -e "${RED}$FAILED Tests failed.${NC}"
fi
if [[ "$ERROR" == "0" ]]; then
    echo -e "${GREEN}0 Tests had errors.${NC}"
else
    echo -e "${RED}$ERROR Tests had errors.${NC}"
fi
exit $((FAILED + ERROR))
