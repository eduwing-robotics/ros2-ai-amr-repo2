# Integrated museum patrol state for Main Server / Unity integration.

# --- Scenario ---
string scenario_id       # idle | exhibit_contact | battery_handoff | night_intruder | exhibit_loss | fire_response
string scenario_label    # Human-readable Korean label
string status            # idle | active
string message           # Detail message for operators

# --- Vision detections ---
bool fire_detected
bool smoke_detected
bool person_detected
string yolo_status_raw   # Raw status string from /detect/status

# --- Gen.G / environment sensors ---
bool pir_active
float32 temperature_c
bool vision_alive
bool night_mode

# --- Robot status ---
float32 battery_pct

# --- Gen.G actuators ---
bool pump_on
bool laser_on

# --- Metadata ---
float64 timestamp        # Unix epoch seconds
