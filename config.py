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


def _get(name, default):
    """Return the override for `name` if one exists, otherwise the default."""
    return _overrides.get(name, default)


# =============================================================================
# 1. PATHS
# =============================================================================
# Top-level project folder; the default paths below are built from it.
# Set it in config_local.py, or with the environment variable NK_PROJECT_ROOT.
PROJECT_ROOT = _get("PROJECT_ROOT", os.environ.get("NK_PROJECT_ROOT"))
if not PROJECT_ROOT:
    raise RuntimeError(
        "PROJECT_ROOT is not set.\n"
        "Copy config_local.example.py to config_local.py and set PROJECT_ROOT, "
        "or try the pipeline on example data with:  python run_pipeline.py --demo"
    )
PROJECT_ROOT = Path(PROJECT_ROOT)

# ---- Inputs ---------------------------------------------------------------
DATA_PATH = Path(_get("DATA_PATH", PROJECT_ROOT / "Data"))                      # Parent data folder
RAW_DATA_PATH = Path(_get("RAW_DATA_PATH", DATA_PATH / "Physiology" / "Raw"))   # One raw file per participant

# Optional CSV of bad ECG samples found by visual inspection
# (columns: participant, signal, onset_sample). None = no masking.
# If the file doesn't exist, masking is skipped automatically.
MANUAL_REJECTION_FILE = _get("MANUAL_REJECTION_FILE", DATA_PATH / "manual_epoch_rejection.csv")

# ---- Outputs --------------------------------------------------------------
OUTPUT_PATH = Path(_get("OUTPUT_PATH", DATA_PATH))                              # Parent output folder

COMBINED_PATH = Path(_get("COMBINED_PATH", OUTPUT_PATH / "Combined"))            # Group-level results CSVs
CLEANED_PATH = Path(_get("CLEANED_PATH", OUTPUT_PATH / "Physiology" / "NeuroKit_Cleaned"))  # Cleaned signals
EPOCHS_PATH = Path(_get("EPOCHS_PATH", OUTPUT_PATH / "Physiology" / "Events"))  # Saved events + epochs (.pkl)
QA_PLOTS_PATH = Path(_get("QA_PLOTS_PATH", OUTPUT_PATH / "Physiology" / "QA_Plots"))  # Interactive QA plots
FIGURES_PATH = Path(_get("FIGURES_PATH", OUTPUT_PATH / "Figures"))               # Group-average figures
LOG_PATH = Path(_get("LOG_PATH", OUTPUT_PATH / "Processing"))                    # Skipped / failed participants
SINGLE_SUBJECT_OUTPUT_PATH = Path(_get("SINGLE_SUBJECT_OUTPUT_PATH", OUTPUT_PATH / "Single_Subject"))

# One cleaned-signal folder per signal type
CLEANED_DIRS = _get("CLEANED_DIRS", {sig: CLEANED_PATH / sig for sig in ("ECG", "EDA", "RSP")})

# Group-level results file per signal type (one row per participant x trial)
COMBINED_FILES = _get("COMBINED_FILES", {
    "ECG": COMBINED_PATH / "ecg_results_combined.csv",
    "EDA": COMBINED_PATH / "eda_results_combined.csv",
    "RSP": COMBINED_PATH / "rsp_results_combined.csv",
})

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

# Digital event/trigger channels. When several channels are passed to
# nk.events_find(), NeuroKit codes each event by the channel's POSITION in
# this list as a power of two: 1st -> 1, 2nd -> 2, 3rd -> 4, 4th -> 8 ...
EVENT_COLUMNS = _get("EVENT_COLUMNS", ["ControlEvent", "DownEvent", "UpEvent"])
EVENT_THRESHOLD = _get("EVENT_THRESHOLD", 0.001)

# Readable condition labels, built from EVENT_COLUMNS so they always match:
# {1: "Control", 2: "Down", 4: "Up"}. Check with 00c_check_events.py.
CONDITION_LABELS = _get(
    "CONDITION_LABELS",
    {2 ** i: col.replace("Event", "") for i, col in enumerate(EVENT_COLUMNS)},
)

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
# Epoch windows in seconds relative to event onset (negative = before onset).
# Used by the 01_ analysis, the 02_ QA plots and the 03_ epochs, so they always match.
# NOTE: ECG start 0.1 means 0.1 s AFTER onset. Use -0.1 for 0.1 s before onset.
EPOCH_WINDOWS = _get("EPOCH_WINDOWS", {
    "ECG": {"start": 0.1, "end": 6},
    "EDA": {"start": 0, "end": 12},
    "RSP": {"start": 0, "end": 6},
})

# ECG masking: seconds masked either side of each bad sample in
# MANUAL_REJECTION_FILE. 0 = nothing is masked. NeuroKit interpolates over
# masked (NaN) samples during cleaning; it does not remove them.
ECG_BAD_WINDOW_SEC = _get("ECG_BAD_WINDOW_SEC", 0)

# QA plots: plot every Nth sample to keep HTML files small (1 = no downsampling)
DOWNSAMPLE_FACTOR = _get("DOWNSAMPLE_FACTOR", 5)

# Re-detect events in 03_ even if saved event files already exist
FORCE_RECREATE_EVENTS = _get("FORCE_RECREATE_EVENTS", False)

# Warn about typos in config_local.py (overrides that match no setting)
_unknown = set(_overrides) - {k for k in globals() if k.isupper()}
if _unknown:
    print(f"[config] Warning: unknown setting(s) in config_local.py ignored: {sorted(_unknown)}")
