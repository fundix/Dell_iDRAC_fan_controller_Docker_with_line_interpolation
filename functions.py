import re
import subprocess

# Global variable to store iDRAC login string, adjust as necessary
# idrac_login_string = "lanplus -H 192.168.2.21 -U fan -P fan"


def run_command(command):
    """Executes a system command and returns its output, suppressing the output."""
    try:
        subprocess.run(command, shell=True, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {command}\n{e}", file=sys.stderr)


def apply_dell_fan_control_profile(idrac_login_string):
    """Applies Dell's default dynamic fan control profile using ipmitool."""
    run_command(f"ipmitool -I {idrac_login_string} raw 0x30 0x30 0x01 0x01")


def apply_user_fan_control_profile(idrac_login_string, hexadecimal_fan_speed):
    """Applies a user-specified static fan control profile using ipmitool."""
    run_command(f"ipmitool -I {idrac_login_string} raw 0x30 0x30 0x01 0x00")
    run_command(
        f"ipmitool -I {idrac_login_string} raw 0x30 0x30 0x02 0xff {hexadecimal_fan_speed}")


def retrieve_temperatures(idrac_login_string):
    data = subprocess.check_output(
        f"ipmitool -I {idrac_login_string} sdr type temperature", shell=True).decode('utf-8')
    pring(f"data {data}")
    # Vyhledání všech teplot
    temperature_readings = re.findall(r'\|\s*(\d{2})\s*degrees C', data)

    # Inicializace proměnných na výchozí hodnoty
    cpu1_temperature = "-"
    inlet_temperature = "-"

    # Přiřazení hodnot podle nalezených teplotních čidel
    if temperature_readings:
        # Předpokládá se, že první teplota je Inlet
        inlet_temperature = temperature_readings[0]
        if len(temperature_readings) >= 2:
            # Předpokládá se, že druhá teplota je CPU1
            cpu1_temperature = temperature_readings[1]

    return int(cpu1_temperature), int(inlet_temperature)


def enable_third_party_pcie_card_dell_default_cooling_response(idrac_login_string):
    """Enables Dell's default cooling response for third-party PCIe cards."""
    run_command(
        f"ipmitool -I {idrac_login_string} raw 0x30 0xce 0x00 0x16 0x05 0x00 0x00 0x00 0x05 0x00 0x00 0x00 0x00")


def disable_third_party_pcie_card_dell_default_cooling_response(idrac_login_string):
    """Disables Dell's default cooling response for third-party PCIe cards."""
    run_command(
        f"ipmitool -I {idrac_login_string} raw 0x30 0xce 0x00 0x16 0x05 0x00 0x00 0x00 0x05 0x00 0x01 0x00 0x00")


def get_dell_server_model(idrac_login_string):
    """Retrieves the Dell server model using ipmitool."""
    fru_content = subprocess.check_output(
        f"ipmitool -I {idrac_login_string} fru", shell=True).decode('utf-8')
    manufacturer = re.search(
        r"Product Manufacturer\s*: (.*)", fru_content).group(1)
    model = re.search(r"Product Name\s*: (.*)", fru_content).group(1)
    return manufacturer, model


def graceful_exit():
    """
        Applies Dell's default fan control profile and enables
        third-party PCIe cooling response on exit.
    """
    apply_dell_fan_control_profile()
    enable_third_party_pcie_card_dell_default_cooling_response()
    print("/!\ WARNING /!\ Container stopped, Dell default dynamic fan control profile applied for safety.")
