# %%
"""
03_epochs_and_average_plots.py — save per-participant events/epochs and plot
group-average responses per condition.

Part 1: for each participant with cleaned data
        - detects events once (from the cleaned RSP file's event columns) and
          saves them to EPOCHS_PATH/sub-XXX_events.pkl
        - cuts epochs for RSP, EDA and ECG using EPOCH_WINDOWS and saves
          EPOCHS_PATH/sub-XXX_<SIGNAL>_epochs.pkl
Part 2: averages the cleaned signal across trials and participants for each
        condition and saves a line plot to FIGURES_PATH.

Requires: 01a/01b/01c to have been run (all three signals).
"""
from pathlib import Path

import matplotlib.pyplot as plt
import neurokit2 as nk
import numpy as np
import pandas as pd
import seaborn as sns

import config as cfg
import utils

SIGNALS = ["RSP", "EDA", "ECG"]
EVENTS_SOURCE = "RSP"   # cleaned file whose event columns are used to find events
epochs_dir = Path(cfg.EPOCHS_PATH)
epochs_dir.mkdir(parents=True, exist_ok=True)


# %%
# ==============================
# Part 1: events + epochs
# ==============================
def load_cleaned_signal(label, signal):
    path = Path(cfg.CLEANED_DIRS[signal]) / f"{label}_{signal}_cleaned.csv"
    if not path.exists():
        raise FileNotFoundError(f"{signal} cleaned file not found: {path}")
    return pd.read_csv(path)


def get_events(label, df):
    """Load saved events, or detect them from df and save."""
    events_file = epochs_dir / f"{label}_events.pkl"
    if events_file.exists() and not cfg.FORCE_RECREATE_EVENTS:
        return pd.read_pickle(events_file)
    for col in cfg.EVENT_COLUMNS:          # guard against a missing channel
        if col not in df.columns:
            df[col] = 0
    ev = utils.find_events(df)
    events = {
        "onset": np.asarray(ev["onset"], dtype=int),
        "duration": np.asarray(ev["duration"], dtype=int),
        "condition": np.asarray(ev["condition"], dtype=int),
        "label": np.asarray(ev["label"], dtype=int),
    }
    pd.to_pickle(events, events_file)
    return events


source_dir = Path(cfg.CLEANED_DIRS[EVENTS_SOURCE])
participants = sorted(
    f.name.split("_")[0] for f in source_dir.glob(f"*_{EVENTS_SOURCE}_cleaned.csv")
) if source_dir.exists() else []
if not participants:
    raise SystemExit(f"No cleaned {EVENTS_SOURCE} files in {source_dir}. Run the 01_ scripts first.")

for label in participants:
    print(f"Processing {label}...")
    try:
        events = get_events(label, load_cleaned_signal(label, EVENTS_SOURCE))
    except Exception as e:
        print(f"  could not get events: {e}")
        continue

    for signal in SIGNALS:
        try:
            signal_df = load_cleaned_signal(label, signal)
        except FileNotFoundError as e:
            print(f"  {e}")
            continue
        epochs = nk.epochs_create(
            signal_df, events,
            sampling_rate=cfg.SAMPLING_RATE,   # cleaned CSVs don't store sampling rate
            epochs_start=cfg.EPOCH_WINDOWS[signal]["start"],
            epochs_end=cfg.EPOCH_WINDOWS[signal]["end"],
        )
        pd.to_pickle(epochs, epochs_dir / f"{label}_{signal}_epochs.pkl")
        print(f"  {signal} epochs saved.")

print("Events and epochs saved.")


# %%
# ==============================
# Part 2: group-average plots
# ==============================
def plot_average_epochs(signal, title=None, participants=None):
    """Average <signal>_Clean across trials and participants, per condition."""
    if participants is None:
        participants = sorted({f.name.split("_")[0] for f in epochs_dir.glob(f"*_{signal}_epochs.pkl")})

    frames = []
    for label in participants:
        f = epochs_dir / f"{label}_{signal}_epochs.pkl"
        if not f.exists():
            print(f"{label} {signal} epochs not found, skipping.")
            continue
        df_long = nk.epochs_to_df(pd.read_pickle(f))
        df_long["participant_id"] = label
        frames.append(df_long)

    if not frames:
        print(f"No {signal} epochs found to plot.")
        return

    col = f"{signal}_Clean"
    combined = pd.concat(frames, ignore_index=True)
    combined["Condition"] = combined["Condition"].replace(cfg.CONDITION_LABELS)
    avg = combined.groupby(["Condition", "Time"])[col].mean().reset_index()

    fig, ax = plt.subplots(figsize=(10, 5))
    sns.lineplot(data=avg, x="Time", y=col, hue="Condition", palette="Set1", ax=ax)
    ax.set(title=title or f"Average {signal} per condition", xlabel="Time (s)", ylabel=col)
    ax.legend(title="Condition")
    fig.tight_layout()

    Path(cfg.FIGURES_PATH).mkdir(parents=True, exist_ok=True)
    out = Path(cfg.FIGURES_PATH) / f"average_{signal}_by_condition.png"
    fig.savefig(out, dpi=150)
    print(f"Saved {out}")
    plt.show()


plot_average_epochs("RSP", "Average respiration (RSP) across conditions")
plot_average_epochs("EDA", "Average electrodermal activity (EDA) across conditions")
plot_average_epochs("ECG", "Average ECG across conditions")
