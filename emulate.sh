#!/bin/bash

CPU_TEMPERATURE_SETPOINT=35
CPU_AVG_TEMPERATURE=55

p="-500"
i="-800"
d="-600"
target=$CPU_TEMPERATURE_SETPOINT
output="0"
currentFeedback="0"
lastPIDError="0"
integralCumulation="0"
maxCumulation="120"
outputLowerBound="10"
outputUpperBound="100"
lastTime=$(date +%s)


function tick() {
    sleep 1s;
    printf "\n"

    # //Retrieve system feedback from user callback.
    currentFeedback=$CPU_AVG_TEMPERATURE
    echo "currentFeedback $currentFeedback"

    # // Calculate the error between the feedback and the target.
    PIDerror=$((target - currentFeedback));

    # currentTime=$(date +%s)
    # deltaTime=$((currentTime - lastTime))
    # # // Calculate the integral of the feedback data since last cycle.
    # cycleIntegral=$(( ((lastPIDError + PIDerror) / 2) * deltaTime ))
    # # // Add this cycle's integral to the integral cumulation.
    # integralCumulation=$(( integralCumulation + cycleIntegral ))
    # # // Calculate the slope of the line with data from the current and last cycles.
    # cycleDerivative=$(( (PIDerror - lastPIDError) / deltaTime ))
    # # // Save time data for next iteration.
    # lastTime=$currentTime;

    integralCumulation=$((integralCumulation + PIDerror));
    cycleDerivative=$((PIDerror - lastPIDError));

    # // Prevent the integral cumulation from becoming overwhelmingly huge.
    if [ $integralCumulation -gt $maxCumulation ];
    then
        integralCumulation=$maxCumulation
    fi

    if [ $integralCumulation -lt -$maxCumulation ];
    then
        integralCumulation=-$maxCumulation;
    fi

    echo "integralCumulation $integralCumulation"
    echo "cycleDerivative $cycleDerivative"
    echo "PIDerror $PIDerror"

    # // Calculate the system output based on data and PID gains.
    output=$(( ((PIDerror * p) + (integralCumulation * i) + (cycleDerivative * d)) / 1000 ));

    echo "output $output"
    # // Save a record of this iteration's data.
    # lastFeedback=$currentFeedback;

    lastPIDError=$PIDerror;
    echo "lastPIDError $lastPIDError"

		# // Trim the output to the bounds if needed.
    if [ $output -gt $outputUpperBound ];
    then
        output=$outputUpperBound
    fi
    if [ $output -lt $outputLowerBound ];
    then
        output=$outputLowerBound
    fi

    echo "output bound $output"
    HEXADECIMAL_FAN_SPEED=$(printf '0x%02x' $output)
}

counter=100
while [ $counter -gt 1 ]; do
    tick
    counter=$((counter - 1))
    if [ $counter -lt 80 ] && [ $CPU_AVG_TEMPERATURE -gt 25 ]; then CPU_AVG_TEMPERATURE=$((CPU_AVG_TEMPERATURE - 1)); fi
done