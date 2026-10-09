"""
config_local.example.py — template for your personal settings.

Copy this file to  config_local.py  and edit it:
    cp config_local.example.py config_local.py        (Mac / Linux)
    copy config_local.example.py config_local.py      (Windows)

config_local.py is git-ignored, so your paths are never committed.
Only include the settings you want to change; everything else uses the
defaults in config.py (see that file for the full list and explanations).
"""

# REQUIRED: folder containing your Data/ folder.
#
# Recommended: keep your data in Box and point to it through Box Drive, so large
# data files don't have to be stored on your computer (see "Running from Box" in
# the README). Box Drive folder locations:
#   Mac:     ~/Library/CloudStorage/Box-Box/...
#   Windows: C:/Users/<your name>/Box/...
# Windows: use forward slashes / (backslashes cause an error).
PROJECT_ROOT = "~/Library/CloudStorage/Box-Box/MyLab/MyStudy"            # Mac
# PROJECT_ROOT = "C:/Users/yourname/Box/MyLab/MyStudy"                   # Windows
# PROJECT_ROOT = "/Users/yourname/Documents/MyStudy"                     # a folder on your own computer

# Optional: point inputs/outputs somewhere other than PROJECT_ROOT/Data/...
# RAW_DATA_PATH = "/path/to/raw/files"
# OUTPUT_PATH = "/path/to/save/outputs"

# Participants to skip (zero-padded strings)
EXCLUDED_PARTICIPANTS = set()

# Participant used by the 00_ test scripts
TEST_PARTICIPANT = "001"

# Uncomment to re-process participants already in the combined CSVs
# RERUN_PROCESSED_PARTICIPANTS = True

# Your trigger channels: {"channel name in your data": "condition label"}.
# Any number of channels (one or more). Default is the lab's three channels:
# EVENT_CHANNELS = {"ControlEvent": "Control", "DownEvent": "Down", "UpEvent": "Up"}

# "fixed"   = triggers mark trial onsets; every epoch is EPOCH_WINDOWS start..end after onset
# "channel" = each event lasts while its trigger channel is ON (blocks of different lengths)
# EVENT_DURATION_MODE = "fixed"

# Epoch windows in seconds per signal ("start" relative to onset; "end" relative to onset in
# "fixed" mode, or to the moment the channel switches off in "channel" mode)
# EPOCH_WINDOWS = {"ECG": {"start": -1, "end": 6},
#                  "EDA": {"start": -1, "end": 12},
#                  "RSP": {"start": -1, "end": 6}}

# HRV: e.g. use only a 5-minute resting baseline at the start for whole-recording HRV
# HRV_SEGMENT_SEC = (0, 300)

# Uncomment and edit if your signal channels have different names
# CHANNEL_RENAME = {"EDA (0 - 35 Hz)": "EDA", "ECG (.5 - 35 Hz)": "ECG", "Respiration": "RSP"}
