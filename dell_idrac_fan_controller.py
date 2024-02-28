import os
import signal
import subprocess
import sys
import time

# Import functions from another file (functions.py needs to be implemented)
from functions import (apply_dell_fan_control_profile, apply_user_fan_control_profile, disable_third_party_pcie_card_dell_default_cooling_response,
                       enable_third_party_pcie_card_dell_default_cooling_response, get_dell_server_model, retrieve_temperatures, graceful_exit)

# Define graceful exit function

# Trap signals for container exit
# Trap signals for container exit
signal.signal(signal.SIGQUIT, graceful_exit)
# signal.signal(signal.SIGKILL, graceful_exit) # Toto je třeba odstranit, nelze zachytit SIGKILL
signal.signal(signal.SIGTERM, graceful_exit)

# Prepare, format, and define initial variables
FAN_SPEED = os.getenv('FAN_SPEED', '5')
CPU_TEMPERATURE_THRESHOLD = int(os.getenv('CPU_TEMPERATURE_THRESHOLD', '50'))
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '60'))
DISABLE_THIRD_PARTY_PCIE_CARD_DELL_DEFAULT_COOLING_RESPONSE = os.getenv(
    'DISABLE_THIRD_PARTY_PCIE_CARD_DELL_DEFAULT_COOLING_RESPONSE', 'false') == 'true'

# Convert FAN_SPEED to hexadecimal if not already
if FAN_SPEED.startswith('0x'):
    decimal_fan_speed = int(FAN_SPEED, 16)
    hexadecimal_fan_speed = FAN_SPEED
else:
    decimal_fan_speed = int(FAN_SPEED)
    hexadecimal_fan_speed = f'0x{decimal_fan_speed: 02x}'

# Check if the iDRAC host is set to 'local'
IDRAC_HOST = os.getenv('IDRAC_HOST', 'local')
if IDRAC_HOST == 'local':
    if not any(os.path.exists(path) for path in ["/dev/ipmi0", "/dev/ipmi/0", "/dev/ipmidev/0"]):
        sys.exit(
            "/!\ Could not open device at /dev/ipmi0 or /dev/ipmi/0 or /dev/ipmidev/0. Exiting.")
    IDRAC_LOGIN_STRING = 'open'
else:
    IDRAC_USERNAME = os.getenv('IDRAC_USERNAME')
    IDRAC_PASSWORD = os.getenv('IDRAC_PASSWORD')
    print(f"iDRAC/IPMI username: {IDRAC_USERNAME}")
    print(f"iDRAC/IPMI password: {IDRAC_PASSWORD}")
    IDRAC_LOGIN_STRING = (
        f"lanplus -H {IDRAC_HOST} -U {IDRAC_USERNAME} -P {IDRAC_PASSWORD}")

server_manufacturer, server_model = get_dell_server_model()
if server_manufacturer != "DELL":
    sys.exit("/!\ Your server isn't a Dell product. Exiting.")

print(f"Server model: {server_manufacturer} {server_model}")
print(f"iDRAC/IPMI host: {IDRAC_HOST}")
print(f"Fan speed objective: {decimal_fan_speed}%")
print(f"CPU temperature threshold: {CPU_TEMPERATURE_THRESHOLD}°C")
print(f"Check interval: {CHECK_INTERVAL}s\n")

TABLE_HEADER_PRINT_INTERVAL = 10
i = TABLE_HEADER_PRINT_INTERVAL
IS_DELL_FAN_CONTROL_PROFILE_APPLIED = True

# Start monitoring
while True:
    time.sleep(CHECK_INTERVAL)

    is_exhaust_temperature_sensor_present, is_cpu2_temperature_sensor_present, exhaust_temperature, cpu1_temperature, cpu2_temperature = retrieve_temperatures()

    # Function definitions for overheating checks
    def cpu1_overheat():
        return cpu1_temperature > CPU_TEMPERATURE_THRESHOLD

    def cpu2_overheat():
        return is_cpu2_temperature_sensor_present and cpu2_temperature > CPU_TEMPERATURE_THRESHOLD

    comment = " -"
    if cpu1_overheat():
        apply_dell_fan_control_profile()
        if not IS_DELL_FAN_CONTROL_PROFILE_APPLIED:
            IS_DELL_FAN_CONTROL_PROFILE_APPLIED = True
            comment = "CPU 1 temperature is too high, Dell default dynamic fan control profile applied for safety"
    elif cpu2_overheat():
        apply_dell_fan_control_profile()
        if not IS_DELL_FAN_CONTROL_PROFILE_APPLIED:
            IS_DELL_FAN_CONTROL_PROFILE_APPLIED = True
            comment = "CPU 2 temperature is too high, Dell default dynamic fan control profile applied for safety"
    else:
        apply_user_fan_control_profile()
        if IS_DELL_FAN_CONTROL_PROFILE_APPLIED:
            IS_DELL_FAN_CONTROL_PROFILE_APPLIED = False
            comment = "CPU temperature decreased and is now OK, user's fan control profile applied."

    # Enable or disable third-party PCIe card Dell default cooling response
    if DISABLE_THIRD_PARTY_PCIE_CARD_DELL_DEFAULT_COOLING_RESPONSE:
        disable_third_party_pcie_card_dell_default_cooling_response()
        third_party_pcie_card_dell_default_cooling_response_status = "Disabled"
    else:
        enable_third_party_pcie_card_dell_default_cooling_response()
        third_party_pcie_card_dell_default_cooling_response_status = "Enabled"

    # Print temperatures and other info
    if i == TABLE_HEADER_PRINT_INTERVAL:
        print("                     ------- Temperatures -------")
        print("    Date & time      Inlet  CPU 1  CPU 2  Exhaust          Active fan speed profile          Third-party PCIe card Dell default cooling response  Comment")
        i = 0
    current_time = time.strftime("%d-%m-%Y %T")
    print(
        f"""{current_time}  {inlet_temperature}°C  {cpu1_temperature}°C  {cpu2_temperature if is_cpu2_temperature_sensor_present else '-'}°C  {exhaust_temperature}
            °C  {'Dynamic' if IS_DELL_FAN_CONTROL_PROFILE_APPLIED else 'Manual'}  {third_party_pcie_card_dell_default_cooling_response_status}  {comment}"""
    )
    i += 1
