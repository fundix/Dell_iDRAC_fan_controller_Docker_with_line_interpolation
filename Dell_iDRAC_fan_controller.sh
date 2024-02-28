#!/bin/bash

# Functions definition
function apply_Dell_fan_control_profile() {
  ipmitool -I $IDRAC_LOGIN_STRING raw 0x30 0x30 0x01 0x01 > /dev/null
  echo "Dell default dynamic fan control profile applied."
}

function apply_user_fan_control_profile() {
  ipmitool -I $IDRAC_LOGIN_STRING raw 0x30 0x30 0x01 0x00 > /dev/null
  ipmitool -I $IDRAC_LOGIN_STRING raw 0x30 0x30 0x02 0xff $HEXADECIMAL_FAN_SPEED > /dev/null
  echo "User static fan control profile ($DECIMAL_FAN_SPEED%) applied."
}

function apply_interpolated_fan_speed() {
  # Calculate interpolated fan speed based on current CPU temperature
  local temp_diff=$((CPU_TEMPERATURE_THRESHOLD - CPU_TEMPERATURE_FOR_START_LINE_INTERPOLATION))
  local current_temp_above_threshold=$((CURRENT_CPU_TEMPERATURE - CPU_TEMPERATURE_FOR_START_LINE_INTERPOLATION))
  local speed_diff=$((DECIMAL_HIGH_FAN_SPEED - DECIMAL_FAN_SPEED))
  local additional_speed=$((speed_diff * current_temp_above_threshold / temp_diff))
  local interpolated_speed=$((DECIMAL_FAN_SPEED + additional_speed))
  if [ $interpolated_speed -gt $DECIMAL_HIGH_FAN_SPEED ]; then
    interpolated_speed=$DECIMAL_HIGH_FAN_SPEED
  fi
  HEXADECIMAL_CURRENT_FAN_SPEED=$(printf '0x%02x' $interpolated_speed)
  ipmitool -I $IDRAC_LOGIN_STRING raw 0x30 0x30 0x01 0x00 > /dev/null
  ipmitool -I $IDRAC_LOGIN_STRING raw 0x30 0x30 0x02 0xff $HEXADECIMAL_CURRENT_FAN_SPEED > /dev/null
  echo "Interpolated fan control profile ($interpolated_speed%) applied."
}

# Main loop
while true; do
  # Retrieve temperatures
  retrieve_temperatures

  # Determine highest CPU temperature
  CURRENT_CPU_TEMPERATURE=$CPU1_TEMPERATURE
  if $IS_CPU2_TEMPERATURE_SENSOR_PRESENT && [ "$CPU2_TEMPERATURE" -gt "$CURRENT_CPU_TEMPERATURE" ]; then
    CURRENT_CPU_TEMPERATURE=$CPU2_TEMPERATURE
  fi

  # Apply appropriate fan control profile
  if [ "$CURRENT_CPU_TEMPERATURE" -le "$CPU_TEMPERATURE_FOR_START_LINE_INTERPOLATION" ]; then
    apply_user_fan_control_profile
  elif [ "$CURRENT_CPU_TEMPERATURE" -ge "$CPU_TEMPERATURE_THRESHOLD" ]; then
    apply_Dell_fan_control_profile
  else
    apply_interpolated_fan_speed
  fi

  # Sleep for the specified interval
  sleep $CHECK_INTERVAL
done
