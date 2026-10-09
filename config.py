"""
config.py — all paths and settings for the pipeline.

DON'T put your own paths in this file. Instead:
    1. Copy  config_local.example.py  ->  config_local.py
    2. Edit config_local.py (it is git-ignored, so your paths stay on your computer
       and `git pull` never conflicts with your settings).

Any UPPER_CASE setting below can be overridden in config_local.py. Settings you
don't override keep the defaults here.

Demo mode: `python run_pipeline.py --demo` (or setting NK_DEMO=1) ignores
config_local.py and runs on simulated data in ./example_data instead.
"""
import os
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent
DEMO_MODE = os.environ.get("NK_DEMO") == "1"

# -----------------------------------------------------------------------------
# Load personal overrides (config_local.py) or demo settings
# -----------------------------------------------------------------------------
_overrides = {}
if DEMO_MODE:
    _overrides = {
        "PROJECT_ROOT": REPO_DIR / "example_data",
        "RAW_FILE_EXTENSION": ".csv",
        "SAMPLING_RATE": 250,
        "EXCLUDED_PARTICIPANTS": {"104"},   # demonstrates exclusion
        "TEST_PARTICIPANT": "101",
        "MANUAL_REJECTION_FILE": None,
    }
else:
    try:
        import config_local as _local
        _overrides = {k: v for k, v in vars(_local).items() if k.isupper()}
    except ImportError:
        pass


def _path(p):
    """Path that also understands '~' (your home folder), e.g. '~/Library/CloudStorage/Box-Box/...'."""
    return Path(p).expanduser() if p is not None else None


def _get(name, default):
    """Return the override for `name` if one exists, otherwise the default."""
    return _overrides.get(name, default)


# =============================================================================
# 1. PATHS
# =============================================================================
# Top-level project folder; the default paths below are built from it.
# Set it in config_local.py, or with the environment variable NK_PROJECT_ROOT.
# It can be a Box Drive folder, so data stay in Box rather than on your disk:
#   Mac:     "~/Library/CloudStorage/Box-Box/<path in Box>"
#   Windows: "C:/Users/<you>/Box/<path in Box>"
PROJECT_ROOT = _get("PROJECT_ROOT", os.environ.get("NK_PROJECT_ROOT"))
if not PROJECT_ROOT:
    raise RuntimeError(
        "PROJECT_ROOT is not set.\n"
        "Copy config_local.example.py to config_local.py and set PROJECT_ROOT, "
        "or try the pipeline on example data with:  python run_pipeline.py --demo"
    )
PROJECT_ROOT = _path(PROJECT_ROOT)

# ---- Inputs ---------------------------------------------------------------
DATA_PATH = _path(_get("DATA_PATH", PROJECT_ROOT / "Data"))                      # Parent data folder
RAW_DATA_PATH = _path(_get("RAW_DATA_PATH", DATA_PATH / "Physiology" / "Raw"))   # One raw file per participant

# Optional CSV of bad samples found by visual inspection, for any signal
# (columns: participant, signal, onset_sample). None = no masking.
# If the file doesn't exist, masking is skipped automatically.
MANUAL_REJECTION_FILE = _path(_get("MANUAL_REJECTION_FILE", DATA_PATH / "manual_epoch_rejection.csv"))

# ---- Outputs --------------------------------------------------------------
OUTPUT_PATH = _path(_get("OUTPUT_PATH", DATA_PATH))                              # Parent output folder

COMBINED_PATH = _path(_get("COMBINED_PATH", OUTPUT_PATH / "Combined"))            # Group-level results CSVs
CLEANED_PATH = _path(_get("CLEANED_PATH", OUTPUT_PATH / "Physiology" / "NeuroKit_Cleaned"))  # Cleaned signals
EPOCHS_PATH = _path(_get("EPOCHS_PATH", OUTPUT_PATH / "Physiology" / "Events"))  # Saved events + epochs (.pkl)
FIGURES_PATH = _path(_get("FIGURES_PATH", OUTPUT_PATH / "Figures"))               # All figures (group averages here)
QA_PLOTS_PATH = _path(_get("QA_PLOTS_PATH", FIGURES_PATH / "QA_Plots"))           # Interactive QA plots
LOG_PATH = _path(_get("LOG_PATH", OUTPUT_PATH / "Processing"))                    # Skipped / failed participants
SINGLE_SUBJECT_OUTPUT_PATH = _path(_get("SINGLE_SUBJECT_OUTPUT_PATH", OUTPUT_PATH / "Single_Subject"))

# One cleaned-signal folder per signal type
CLEANED_DIRS = _get("CLEANED_DIRS", {sig: CLEANED_PATH / sig for sig in ("ECG", "EDA", "RSP")})

# Group-level results file per signal type (one row per participant x trial)
COMBINED_FILES = _get("COMBINED_FILES", {
    "ECG": COMBINED_PATH / "ecg_results_combined.csv",
    "EDA": COMBINED_PATH / "eda_results_combined.csv",
    "RSP": COMBINED_PATH / "rsp_results_combined.csv",
})
CLEANED_DIRS = {k: _path(v) for k, v in CLEANED_DIRS.items()}
COMBINED_FILES = {k: _path(v) for k, v in COMBINED_FILES.items()}
# Whole-recording HRV results (one row per participant)
HRV_FILE = _path(_get("HRV_FILE", COMBINED_PATH / "hrv_results_combined.csv"))

# =============================================================================
# 2. DATA FORMAT  (defaults match the lab's BIOPAC AcqKnowledge setup)
# =============================================================================
# Raw file type. utils.load_raw_data() reads .acq (AcqKnowledge) and .csv.
RAW_FILE_EXTENSION = _get("RAW_FILE_EXTENSION", ".acq")

# Participant ID = first N characters of the raw filename ("012_filtered_chopped.acq" -> "012")
PARTICIPANT_ID_LENGTH = _get("PARTICIPANT_ID_LENGTH", 3)

# Rename raw channel names -> short names used by the scripts
CHANNEL_RENAME = _get("CHANNEL_RENAME", {
    "EDA (0 - 35 Hz)": "EDA",
    "ECG (.5 - 35 Hz)": "ECG",
    "Respiration": "RSP",
})

# Event (trigger) channels: {channel name in your data: condition label}.
# Use as many channels as you have (one or more). Each time a channel switches
# on (goes above EVENT_THRESHOLD) counts as one event of that condition.
#   One channel:    EVENT_CHANNELS = {"Stimulus": "Stimulus"}
#   Four channels:  EVENT_CHANNELS = {"Ch1": "Rest", "Ch2": "Low", "Ch3": "High", "Ch4": "Recovery"}
# A plain list also works; the channel names are then used as labels.
EVENT_CHANNELS = _get("EVENT_CHANNELS", {
    "ControlEvent": "Control",
    "DownEvent": "Down",
    "UpEvent": "Up",
})
if not isinstance(EVENT_CHANNELS, dict):
    EVENT_CHANNELS = {ch: ch for ch in EVENT_CHANNELS}
EVENT_COLUMNS = list(EVENT_CHANNELS)          # channel names only (used internally)
if "EVENT_COLUMNS" in _overrides:
    raise ValueError("EVENT_COLUMNS is no longer used: set EVENT_CHANNELS in config_local.py instead.")

# A channel counts as "on" while its value is above this threshold.
EVENT_THRESHOLD = _get("EVENT_THRESHOLD", 0.001)
# Ignore "events" shorter than this (seconds), e.g. 0.005 to drop trigger glitches.
# 0 = keep everything (NeuroKit's default of at least 1 sample).
EVENT_MIN_DURATION_SEC = _get("EVENT_MIN_DURATION_SEC", 0)

# How long is each event?
#   "fixed"   - only the ONSET matters; how long the trigger stays on is ignored.
#               Every epoch has the same length, set by EPOCH_WINDOWS start/end
#               (relative to onset). Use this when the trigger marks the start of
#               a trial whose length is fixed by your task (e.g. a 100 ms pulse at
#               the start of every 6 s trial).
#   "channel" - the event lasts as long as the channel stays ON (onset -> offset).
#               Epochs run from onset + start until the channel switches off,
#               plus `end` seconds. Use this when the channel stays high for the
#               whole trial/block and blocks differ in length.
EVENT_DURATION_MODE = _get("EVENT_DURATION_MODE", "fixed")

# Sampling rate (Hz). Used for .csv raw files, and when re-loading cleaned
# CSVs (which don't store it). .acq files report their own rate.
SAMPLING_RATE = _get("SAMPLING_RATE", 1000)

# =============================================================================
# 3. PARTICIPANTS
# =============================================================================
# Participant IDs (strings, zero-padded) to always skip.
EXCLUDED_PARTICIPANTS = set(_get("EXCLUDED_PARTICIPANTS", set()))

# False = skip participants already in the combined CSV (resume an interrupted run)
# True  = re-process everyone, replacing their previous rows
RERUN_PROCESSED_PARTICIPANTS = _get("RERUN_PROCESSED_PARTICIPANTS", False)

# Participant used by the 00_ single-subject scripts
TEST_PARTICIPANT = _get("TEST_PARTICIPANT", "001")

# =============================================================================
# 4. ANALYSIS SETTINGS
# =============================================================================
# Epoch windows (seconds), per signal. Used by the 01_ analysis, the 02_ QA
# plots and the 03_ epochs, so they always match.
#   start: relative to event ONSET (negative = before onset, e.g. -0.5 for a baseline).
#   end:   "fixed" mode   -> seconds after ONSET.
#          "channel" mode -> extra seconds after the channel switches OFF (0 = stop at offset).
# NOTE: ECG start 0.1 means 0.1 s AFTER onset. Use -0.1 for 0.1 s before onset.
EPOCH_WINDOWS = _get("EPOCH_WINDOWS", {
    "ECG": {"start": 0.1, "end": 6},
    "EDA": {"start": 0, "end": 12},
    "RSP": {"start": 0, "end": 6},
})

# HRV (heart rate variability), computed in 01a_process_ecg.py --------------
# Whole-recording HRV: one row per participant in HRV_FILE (time, frequency
# and non-linear indices). Use HRV_SEGMENT_SEC to restrict it to part of the
# recording, e.g. (0, 300) = a 5-minute resting baseline at the start.
HRV_WHOLE_RECORDING = _get("HRV_WHOLE_RECORDING", True)
HRV_SEGMENT_SEC = _get("HRV_SEGMENT_SEC", None)            # None = whole recording
HRV_INDICES = _get("HRV_INDICES", ["time", "frequency", "nonlinear"])
# Per-epoch HRV: time-domain indices (e.g. HRV_RMSSD, HRV_SDNN) added to each
# trial's row in the ECG results, for epochs at least HRV_MIN_EPOCH_SEC long.
# Shorter epochs get empty HRV columns: HRV from a few beats isn't meaningful.
HRV_PER_EPOCH = _get("HRV_PER_EPOCH", True)
HRV_MIN_EPOCH_SEC = _get("HRV_MIN_EPOCH_SEC", 30)
# Re-detect R-peaks with NeuroKit's artifact correction (fixes missed/extra
# beats) before computing HRV. Recommended.
HRV_CORRECT_ARTIFACTS = _get("HRV_CORRECT_ARTIFACTS", True)

# Manual masking (any signal): seconds masked either side of each bad sample
# listed in MANUAL_REJECTION_FILE. One number for all signals, or per signal,
# e.g. {"ECG": 1, "EDA": 2, "RSP": 2}. 0 = nothing is masked.
# NeuroKit fills masked (NaN) samples with the last good value during cleaning
# (a flat segment); it does not remove them.
MASK_WINDOW_SEC = _get("MASK_WINDOW_SEC", 0)

# QA plots: plot every Nth sample to keep HTML files small (1 = no downsampling)
DOWNSAMPLE_FACTOR = _get("DOWNSAMPLE_FACTOR", 5)

# Re-detect events in 03_ even if saved event files already exist
FORCE_RECREATE_EVENTS = _get("FORCE_RECREATE_EVENTS", False)

if EVENT_DURATION_MODE not in ("fixed", "channel"):
    raise ValueError(f"EVENT_DURATION_MODE must be 'fixed' or 'channel', not {EVENT_DURATION_MODE!r}")
_no_window = set(CLEANED_DIRS) - set(EPOCH_WINDOWS)
if _no_window:
    raise ValueError(f"EPOCH_WINDOWS is missing an entry for: {sorted(_no_window)}")

# Warn about typos in config_local.py (overrides that match no setting)
_unknown = set(_overrides) - {k for k in globals() if k.isupper()}
if _unknown:
    print(f"[config] Warning: unknown setting(s) in config_local.py ignored: {sorted(_unknown)}")
