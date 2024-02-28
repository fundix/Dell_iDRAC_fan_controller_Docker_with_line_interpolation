from functions import (retrieve_temperatures, apply_user_fan_control_profile,
                       apply_dell_fan_control_profile,
                       disable_third_party_pcie_card_dell_default_cooling_response,
                       enable_third_party_pcie_card_dell_default_cooling_response,
                       get_dell_server_model, graceful_exit)


# print(retrieve_temperatures())
apply_user_fan_control_profile(0x34)
# apply_dell_fan_control_profile()
# disable_third_party_pcie_card_dell_default_cooling_response()
# enable_third_party_pcie_card_dell_default_cooling_response()
# print(graceful_exit())
