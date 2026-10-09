"""
config_local.example.py — template for your personal settings.

Copy this file to  config_local.py  and edit it:
    cp config_local.example.py config_local.py        (Mac / Linux)
    copy config_local.example.py config_local.py      (Windows)

config_local.py is git-ignored, so your paths are never committed.
Only include the settings you want to change; everything else uses the
defaults in config.py (see that file for the full list and explanations).
"""

# REQUIRED: folder containing your Data/ folder
PROJECT_ROOT = "/path/to/your/project"

# Optional: point inputs/outputs somewhere other than PROJECT_ROOT/Data/...
# RAW_DATA_PATH = "/path/to/raw/files"
# OUTPUT_PATH = "/path/to/save/outputs"

# Participants to skip (zero-padded strings)
EXCLUDED_PARTICIPANTS = set()

# Participant used by the 00_ test scripts
TEST_PARTICIPANT = "001"

# Uncomment to re-process participants already in the combined CSVs
# RERUN_PROCESSED_PARTICIPANTS = True

# Uncomment and edit if your channel names differ from the lab defaults
# CHANNEL_RENAME = {"EDA (0 - 35 Hz)": "EDA", "ECG (.5 - 35 Hz)": "ECG", "Respiration": "RSP"}
# EVENT_COLUMNS = ["ControlEvent", "DownEvent", "UpEvent"]
