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
HIGH_FAN_SPEED = os.getenv('HIGH_FAN_SPEED', '70')
CPU_TEMPERATURE_THRESHOLD = int(os.getenv('CPU_TEMPERATURE_THRESHOLD', '50'))
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '60'))
DISABLE_THIRD_PARTY_PCIE_CARD_DELL_DEFAULT_COOLING_RESPONSE = os.getenv(
    'DISABLE_THIRD_PARTY_PCIE_CARD_DELL_DEFAULT_COOLING_RESPONSE', 'false') == 'true'
IDRAC_LOGIN_STRING = ''

CPU_TEMPERATURE_FOR_START_LINE_INTERPOLATION = os.getenv(
    'CPU_TEMPERATURE_FOR_START_LINE_INTERPOLATION', '40')

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
print(f"Fan speed min: {FAN_SPEED}%")
print(f"Fan speed max: {HIGH_FAN_SPEED}%")
print(f"CPU temperature threshold: {CPU_TEMPERATURE_THRESHOLD}°C")
print(f"Check interval: {CHECK_INTERVAL}s\n")

TABLE_HEADER_PRINT_INTERVAL = 10
i = TABLE_HEADER_PRINT_INTERVAL
IS_DELL_FAN_CONTROL_PROFILE_APPLIED = True

# Enable or disable third-party PCIe card Dell default cooling response
if DISABLE_THIRD_PARTY_PCIE_CARD_DELL_DEFAULT_COOLING_RESPONSE:
    disable_third_party_pcie_card_dell_default_cooling_response(
        IDRAC_LOGIN_STRING)
    third_party_pcie_card_dell_default_cooling_response_status = "Disabled"
else:
    enable_third_party_pcie_card_dell_default_cooling_response(
        IDRAC_LOGIN_STRING)
    third_party_pcie_card_dell_default_cooling_response_status = "Enabled"


def calculate_fan_speed(cpu_temperature, start_temp, threshold_temp, low_speed, high_speed):
    if cpu_temperature <= start_temp:
        return low_speed
    elif cpu_temperature >= threshold_temp:
        return high_speed
    else:
        # Lineární interpolace mezi start_temp a threshold_temp
        slope = (high_speed - low_speed) / (threshold_temp - start_temp)
        return low_speed + slope * (cpu_temperature - start_temp)


def apply_interpolated_fan_speed(idrac_login_string, cpu_temperature):
    # Převod rychlostí ventilátoru z hex na dec
    low_speed_dec = int(FAN_SPEED)
    high_speed_dec = int(HIGH_FAN_SPEED, 16)

    # Výpočet cílové rychlosti
    target_speed = calculate_fan_speed(
        cpu_temperature, CPU_TEMPERATURE_FOR_START_LINE_INTERPOLATION,
        CPU_TEMPERATURE_THRESHOLD, low_speed_dec, high_speed_dec)

    # Převod cílové rychlosti zpět na hexadecimální formát
    target_speed_hex = f"0x{int(target_speed): 02x}"

    # Aplikace cílové rychlosti ventilátoru
    apply_user_fan_control_profile(idrac_login_string, target_speed_hex)

    return target_speed


target = 0

# Start monitoring
while True:
    time.sleep(CHECK_INTERVAL)

    inlet_temperature, cpu1_temperature = retrieve_temperatures(
        IDRAC_LOGIN_STRING)

    if cpu1_temperature > CPU_TEMPERATURE_FOR_START_LINE_INTERPOLATION:
        # Aplikujeme interpolovanou rychlost ventilátoru
        target = apply_interpolated_fan_speed(
            IDRAC_LOGIN_STRING, cpu1_temperature)
        comment = "Interpolated fan speed applied based on CPU temperature."
    else:
        # Aplikujeme výchozí nebo nízkou rychlost ventilátoru
        apply_user_fan_control_profile(
            IDRAC_LOGIN_STRING, f"0x{int(FAN_SPEED): 02x}")
        target = FAN_SPEED
        comment = "Default or low fan speed applied."

    # Print temperatures and other info
    if i == TABLE_HEADER_PRINT_INTERVAL:
        print("                     ------- Temperatures -------")
        print("    Date & time      Inlet  CPU 1  Target   Active fan speed profile          Third-party PCIe card Dell default cooling response  Comment")
        i = 0
    current_time = time.strftime("%d-%m-%Y %T")
    print(
        f"""{current_time}  {inlet_temperature}°C  {cpu1_temperature}°C {target}  {'Dynamic' if IS_DELL_FAN_CONTROL_PROFILE_APPLIED else 'Manual'}  {
            third_party_pcie_card_dell_default_cooling_response_status}  {comment}"""
    )
    i += 1
