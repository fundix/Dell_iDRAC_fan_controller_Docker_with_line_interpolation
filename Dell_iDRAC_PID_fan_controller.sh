#!/bin/bash

# Enable strict bash mode
set -euo pipefail

# Function to apply Dell's default dynamic fan control profile
function apply_Dell_fan_control_profile () {
  ipmitool -I "$IDRAC_LOGIN_STRING" raw 0x30 0x30 0x01 0x01 > /dev/null
  CURRENT_FAN_CONTROL_PROFILE="Dell default dynamic fan control profile"
}

# Function to apply a user-specified static fan control profile
function apply_user_fan_control_profile () {
  ipmitool -I "$IDRAC_LOGIN_STRING" raw 0x30 0x30 0x01 0x00 > /dev/null
  ipmitool -I "$IDRAC_LOGIN_STRING" raw 0x30 0x30 0x02 0xff "$HEXADECIMAL_FAN_SPEED" > /dev/null
  CURRENT_FAN_CONTROL_PROFILE="User dynamic fan control profile"
}

# Function to retrieve and print current fan speeds
function print_current_fan_speed () {
  local FAN_SPEEDS
  FAN_SPEEDS=$(ipmitool -I "$IDRAC_LOGIN_STRING" sdr type Fan)
  echo "Current fan speeds:"
  echo "$FAN_SPEEDS"
}

# Function to retrieve temperature sensors data
function retrieve_temperatures () {
  if (( $# != 2 )); then
    printf "Illegal number of parameters.\nUsage: retrieve_temperatures \$IS_EXHAUST_TEMPERATURE_SENSOR_PRESENT \$IS_CPU2_TEMPERATURE_SENSOR_PRESENT" >&2
    return 1
  fi
  local IS_EXHAUST_TEMPERATURE_SENSOR_PRESENT=$1
  local IS_CPU2_TEMPERATURE_SENSOR_PRESENT=$2

  local DATA
  DATA=$(ipmitool -I "$IDRAC_LOGIN_STRING" sdr type temperature | grep degrees)

  # Parse CPU and inlet data
  CPU1_TEMPERATURE=$(echo "$DATA" | grep "CPU1 Temp" | grep -Po '\d{2}' | tail -1)
  CPU2_TEMPERATURE=$(echo "$DATA" | grep "CPU2 Temp" | grep -Po '\d{2}' | tail -1)
  INLET_TEMPERATURE=$(echo "$DATA" | grep "Inlet Temp" | grep -Po '\d{2}' | tail -1)
  EXHAUST_TEMPERATURE=$(echo "$DATA" | grep "Exhaust Temp" | grep -Po '\d{2}' | tail -1)

  # Calculate average CPU temperature
  CPU_AVG_TEMPERATURE=$(( (CPU1_TEMPERATURE + CPU2_TEMPERATURE) / 2 ))
}

# Function for graceful exit
function graceful_exit () {
  apply_Dell_fan_control_profile
  echo "/!\ WARNING /!\ Service stopped, Dell default dynamic fan control profile applied for safety."
  exit 0
}

trap 'graceful_exit' SIGQUIT SIGTERM SIGINT

# Check and set initial variables
IDRAC_LOGIN_STRING="lanplus -H $IDRAC_HOST -U $IDRAC_USERNAME -P $IDRAC_PASSWORD"

# Define PID controller variables
p=-500
i=-800
d=-600
target=$CPU_TEMPERATURE_SETPOINT
output=0
currentFeedback=0
lastPIDError=0
integralCumulation=0
maxCumulation=120
outputLowerBound=10
outputUpperBound=100
lastTime=$(date +%s)

# PID tick function
function tickPID() {
    currentFeedback=$CPU_AVG_TEMPERATURE
    PIDerror=$((target - currentFeedback))

    currentTime=$(date +%s)
    deltaTime=$((currentTime - lastTime))
    if [ $deltaTime -eq 0 ]; then
        deltaTime=1
    fi
    cycleIntegral=$(( ((lastPIDError + PIDerror) / 2) * deltaTime ))
    integralCumulation=$(( integralCumulation + cycleIntegral ))
    cycleDerivative=$(( (PIDerror - lastPIDError) / deltaTime ))
    lastTime=$currentTime

    if [ $integralCumulation -gt $maxCumulation ]; then
        integralCumulation=$maxCumulation
    elif [ $integralCumulation -lt -$maxCumulation ]; then
        integralCumulation=-$maxCumulation
    fi

    output=$(( ((PIDerror * p) + (integralCumulation * i) + (cycleDerivative * d)) / 1000 ))

    if [ $output -gt $outputUpperBound ]; then
        output=$outputUpperBound
    elif [ $output -lt $outputLowerBound ]; then
        output=$outputLowerBound
    fi

    HEXADECIMAL_FAN_SPEED=$(printf '0x%02x' $output)
}

# Main monitoring loop
while true; do
  sleep $CHECK_INTERVAL &
  SLEEP_PROCESS_PID=$!

  retrieve_temperatures $IS_EXHAUST_TEMPERATURE_SENSOR_PRESENT $IS_CPU2_TEMPERATURE_SENSOR_PRESENT

  # PID Controller
  tickPID
  apply_user_fan_control_profile

  # Print current fan speed
  print_current_fan_speed

  wait $SLEEP_PROCESS_PID
done
