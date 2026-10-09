"""
utils.py — small helpers shared by all pipeline scripts.

If your raw data are not AcqKnowledge (.acq) files, load_raw_data() is the
only function you need to change.
"""
from datetime import datetime
from pathlib import Path

import neurokit2 as nk
import pandas as pd

import config as cfg


# -----------------------------------------------------------------------------
# Loading raw data
# -----------------------------------------------------------------------------
def load_raw_data(file_path):
    """Load one raw recording and rename channels.

    Returns (data: DataFrame, sampling_rate: int).
    Supports AcqKnowledge (.acq) and CSV (one column per channel, sampled at
    cfg.SAMPLING_RATE). Add another `elif` here for other file types.
    """
    suffix = Path(file_path).suffix.lower()
    if suffix == ".acq":
        data, sampling_rate = nk.read_acqknowledge(str(file_path))
    elif suffix == ".csv":
        data, sampling_rate = pd.read_csv(file_path), cfg.SAMPLING_RATE
    else:
        raise ValueError(f"Don't know how to read '{suffix}' files. Edit utils.load_raw_data().")
    data = data.rename(columns=cfg.CHANNEL_RENAME)
    return data, sampling_rate


def participant_id_from_filename(filename):
    """'012_filtered_chopped.acq' -> '012'"""
    return Path(filename).name[: cfg.PARTICIPANT_ID_LENGTH].zfill(cfg.PARTICIPANT_ID_LENGTH)


def participant_label(participant_id):
    """'012' -> 'sub-012'"""
    return f"sub-{participant_id}"


def list_raw_files():
    """All raw files in RAW_DATA_PATH, sorted."""
    raw_dir = Path(cfg.RAW_DATA_PATH)
    if not raw_dir.exists():
        raise FileNotFoundError(
            f"RAW_DATA_PATH does not exist: {raw_dir}\n"
            "Edit PROJECT_ROOT / RAW_DATA_PATH in config.py."
        )
    return sorted(p for p in raw_dir.iterdir() if p.suffix == cfg.RAW_FILE_EXTENSION)


def find_raw_file(participant_id):
    """Return the raw file whose name starts with this participant ID, or None."""
    for path in list_raw_files():
        if participant_id_from_filename(path.name) == participant_id:
            return path
    return None


# -----------------------------------------------------------------------------
# Events
# -----------------------------------------------------------------------------
def find_events(data):
    """Detect task events from the event channels defined in config."""
    return nk.events_find(
        data[cfg.EVENT_COLUMNS],
        threshold=cfg.EVENT_THRESHOLD,
        threshold_keep="above",
    )


def tidy_results(df, label):
    """Add participant column, readable condition names and rename Label -> Trial."""
    df = df.copy()
    df.insert(0, "participant_id", label)
    df["Condition"] = df["Condition"].replace(cfg.CONDITION_LABELS)
    return df.rename(columns={"Label": "Trial"})


# -----------------------------------------------------------------------------
# Combined results + logging
# -----------------------------------------------------------------------------
def load_combined(path):
    """Load an existing combined results CSV (or an empty frame)."""
    path = Path(path)
    if path.exists():
        df = pd.read_csv(path)
        df["participant_id"] = df["participant_id"].astype(str)
        return df
    return pd.DataFrame()


def processed_ids(combined_df):
    """Set of participant IDs ('012') already present in a combined CSV."""
    if combined_df.empty:
        return set()
    return set(
        combined_df["participant_id"].str.replace("sub-", "").str.zfill(cfg.PARTICIPANT_ID_LENGTH)
    )


class Logger:
    """Prints a message and appends it to a log file in LOG_PATH."""

    def __init__(self, name):
        Path(cfg.LOG_PATH).mkdir(parents=True, exist_ok=True)
        self.path = Path(cfg.LOG_PATH) / f"log_{name}.txt"

    def __call__(self, message, echo=True):
        if echo:
            print(message)
        with open(self.path, "a") as f:
            f.write(message + "\n")

    def start(self, title):
        self(f"\n--- {title} started: {datetime.now()} ---", echo=False)
        self(f"RERUN_PROCESSED_PARTICIPANTS = {cfg.RERUN_PROCESSED_PARTICIPANTS}", echo=False)

    def finish(self, title):
        self(f"--- {title} finished: {datetime.now()} ---", echo=False)
