"""
utils.py — small helpers shared by all pipeline scripts.

If your raw data are not AcqKnowledge (.acq) files, load_raw_data() is the
only function you need to change.
"""
import warnings
from datetime import datetime
from pathlib import Path

import neurokit2 as nk
import numpy as np
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
    data.attrs["sampling_rate"] = sampling_rate
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
    """Detect events on every channel in cfg.EVENT_CHANNELS using NeuroKit.

    Each channel is passed separately to nk.events_find(), which finds every time
    the channel goes above EVENT_THRESHOLD (onset) and how long it stays there
    (duration). Each channel's events get that channel's condition label, and
    nk.events_create() combines all channels into one events dict, sorted by
    onset, with trial labels "1", "2", ... This works for one channel or many.

    (Passing several channels to nk.events_find() at once would merge them into
    numeric codes 1, 2, 4, ... and passing a single-column table makes it crash,
    so channels are processed one at a time.)
    """
    missing = [ch for ch in cfg.EVENT_CHANNELS if ch not in data.columns]
    if missing:
        raise KeyError(
            f"Event channel(s) {missing} not found. Columns in file: {list(data.columns)}. "
            "Check EVENT_CHANNELS in your config_local.py."
        )

    onsets, durations, conditions = [], [], []
    for channel, condition in cfg.EVENT_CHANNELS.items():
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")      # "no events found" is reported by 00c instead
            ev = nk.events_find(
                data[channel].astype(float),     # one channel at a time (a 1-D signal)
                threshold=cfg.EVENT_THRESHOLD,
                threshold_keep="above",
                duration_min=max(1, int(cfg.EVENT_MIN_DURATION_SEC * _sampling_rate_hint(data))),
            )
        onsets += list(ev["onset"])
        durations += list(ev["duration"])
        conditions += [condition] * len(ev["onset"])

    order = np.argsort(onsets, kind="stable")
    return nk.events_create(
        event_onsets=np.array(onsets, dtype=int)[order],
        event_durations=np.array(durations, dtype=int)[order],
        event_conditions=[conditions[i] for i in order],
    )


def _sampling_rate_hint(data):
    """Sampling rate attached to the data by load_raw_data (falls back to config)."""
    return data.attrs.get("sampling_rate", cfg.SAMPLING_RATE)


def epoch_window(events, signal, sampling_rate):
    """Return (epochs_start, epochs_end) in seconds for nk.epochs_create.

    EVENT_DURATION_MODE = "fixed":   every epoch runs from onset+start to onset+end.
    EVENT_DURATION_MODE = "channel": each epoch runs from onset+start until the
                                     trigger channel switches off, plus `end` seconds.
    """
    win = cfg.EPOCH_WINDOWS[signal]
    if cfg.EVENT_DURATION_MODE == "fixed":
        return win["start"], win["end"]
    if cfg.EVENT_DURATION_MODE == "channel":
        if win["end"] == 0:
            return win["start"], "from_events"     # NeuroKit: epoch ends when the channel switches off
        return win["start"], [d / sampling_rate + win["end"] for d in events["duration"]]
    raise ValueError(f"EVENT_DURATION_MODE must be 'fixed' or 'channel', not {cfg.EVENT_DURATION_MODE!r}")


def epoch_ends(events, signal, sampling_rate):
    """End of each event's epoch, in seconds after its onset (one value per event)."""
    win = cfg.EPOCH_WINDOWS[signal]
    if cfg.EVENT_DURATION_MODE == "fixed":
        return [win["end"]] * len(events["onset"])
    return [d / sampling_rate + win["end"] for d in events["duration"]]


def make_epochs(data_clean, events, signal, sampling_rate):
    """Cut epochs for one signal using the configured window / duration mode."""
    start, end = epoch_window(events, signal, sampling_rate)
    return nk.epochs_create(data_clean, events, sampling_rate=sampling_rate,
                            epochs_start=start, epochs_end=end)


# -----------------------------------------------------------------------------
# Manual masking of bad segments (all signals)
# -----------------------------------------------------------------------------
_REJECTIONS = None


def _load_rejections():
    """Read MANUAL_REJECTION_FILE once (empty table if not set / not found)."""
    global _REJECTIONS
    if _REJECTIONS is None:
        path = cfg.MANUAL_REJECTION_FILE
        if path and Path(path).exists():
            # keep_default_na=False so a literal "NA" stays text (pandas would turn it into NaN)
            _REJECTIONS = pd.read_csv(path, dtype=str, keep_default_na=False)
            _REJECTIONS.columns = [c.strip() for c in _REJECTIONS.columns]
        else:
            _REJECTIONS = pd.DataFrame(columns=["participant", "signal", "onset_sample"])
    return _REJECTIONS


def mask_window_sec(signal):
    """MASK_WINDOW_SEC for this signal (a single number, or a dict per signal)."""
    w = cfg.MASK_WINDOW_SEC
    return w.get(signal, 0) if isinstance(w, dict) else w


def apply_manual_masking(raw, label, signal, sampling_rate):
    """Mask bad samples listed in MANUAL_REJECTION_FILE for this participant + signal.

    Returns the signal with masked samples set to NaN, or None if the file marks
    this participant's signal as unusable (onset_sample = "NA").
    Each listed sample is masked +/- MASK_WINDOW_SEC seconds. NeuroKit's cleaning
    then fills masked samples with the last good value (a flat segment).
    """
    raw = raw.astype(float).copy()
    rej = _load_rejections()
    rows = rej[(rej["participant"].str.strip() == label) &
               (rej["signal"].str.strip().str.upper() == signal.upper())]
    if rows.empty:
        return raw
    onsets = rows["onset_sample"].astype(str).str.strip()
    if onsets.str.upper().eq("NA").any():
        return None
    half = int(mask_window_sec(signal) * sampling_rate)
    if half > 0:
        for onset in onsets.astype(int):
            raw.iloc[max(0, onset - half): min(len(raw), onset + half)] = np.nan
        print(f"{label}: masked {len(onsets)} {signal} segment(s) "
              f"({raw.isna().mean() * 100:.2f}% of signal)")
    return raw


# -----------------------------------------------------------------------------
# HRV
# -----------------------------------------------------------------------------
def hrv_peaks(ecg_clean, sampling_rate):
    """R-peak sample indices for HRV (with artifact correction if configured)."""
    _, info = nk.ecg_peaks(ecg_clean, sampling_rate=sampling_rate,
                           correct_artifacts=cfg.HRV_CORRECT_ARTIFACTS)
    return np.asarray(info["ECG_R_Peaks"])


def hrv_whole(peaks, sampling_rate, label):
    """One-row DataFrame of HRV indices for the whole recording (or HRV_SEGMENT_SEC)."""
    if cfg.HRV_SEGMENT_SEC is not None:
        lo, hi = (int(t * sampling_rate) for t in cfg.HRV_SEGMENT_SEC)
        peaks = peaks[(peaks >= lo) & (peaks < hi)]
    funcs = {"time": nk.hrv_time, "frequency": nk.hrv_frequency, "nonlinear": nk.hrv_nonlinear}
    parts = [funcs[i](peaks, sampling_rate=sampling_rate) for i in cfg.HRV_INDICES]
    out = pd.concat(parts, axis=1)
    out.insert(0, "HRV_Duration_s", (peaks[-1] - peaks[0]) / sampling_rate if len(peaks) > 1 else 0)
    out.insert(0, "HRV_N_Beats", len(peaks))
    out.insert(0, "participant_id", label)
    return out


def hrv_per_epoch(peaks, events, sampling_rate):
    """Time-domain HRV for each epoch at least HRV_MIN_EPOCH_SEC long.

    Returns a DataFrame indexed by trial label (same as the ECG results' Trial),
    or None if no epoch is long enough.
    """
    start = cfg.EPOCH_WINDOWS["ECG"]["start"]
    ends = epoch_ends(events, "ECG", sampling_rate)
    rows = {}
    for onset, end, trial in zip(events["onset"], ends, events["label"]):
        if end - start < cfg.HRV_MIN_EPOCH_SEC:
            continue
        lo, hi = onset + int(start * sampling_rate), onset + int(end * sampling_rate)
        p = peaks[(peaks >= lo) & (peaks < hi)]
        if len(p) < 3:
            continue
        rows[trial] = nk.hrv_time(p, sampling_rate=sampling_rate).iloc[0]
    return pd.DataFrame(rows).T if rows else None


def tidy_results(df, label):
    """Add participant column and rename Label -> Trial."""
    df = df.copy()
    df.insert(0, "participant_id", label)
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
