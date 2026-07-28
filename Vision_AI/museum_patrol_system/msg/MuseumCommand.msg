# Command from Main Server / Unity to scenario manager.

# command_type values:
#   exhibit_loss     - trigger/clear exhibit loss scenario (use active)
#   set_night_mode   - toggle night patrol mode (use night_mode)
#   force_scenario   - force a scenario (use scenario_id)
#   clear_force      - clear forced scenario and exhibit_loss flag
string command_type

# Target scenario for force_scenario:
#   idle | exhibit_contact | battery_handoff | night_intruder | exhibit_loss | fire_response
string scenario_id

# exhibit_loss: true=trigger, false=clear
bool active

# set_night_mode: true=night patrol, false=day/open hours
bool night_mode
