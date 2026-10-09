# %%
"""
03_epochs_and_average_plots.py — save per-participant events/epochs and plot
group-average responses per condition.

Part 1: for each participant with cleaned data
        - detects events once (from the trigger channels kept in its first
          available cleaned file) and saves them to EPOCHS_PATH/sub-XXX_events.pkl
        - cuts epochs for each signal using EPOCH_WINDOWS / EVENT_DURATION_MODE
          and saves EPOCHS_PATH/sub-XXX_<SIGNAL>_epochs.pkl
Part 2: averages the cleaned EDA signal across trials and participants for
        each condition and saves a line plot to FIGURES_PATH.

Requires: at least one of 01a/01b/01c to have been run.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import neurokit2 as nk
import pandas as pd
import seaborn as sns

import config as cfg
import utils

SIGNALS = ["RSP", "EDA", "ECG"]
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
        events = pd.read_pickle(events_file)
        # Only reuse saved events if they use the current condition labels
        if set(events["condition"]) <= set(cfg.EVENT_CHANNELS.values()):
            return events
        print("  saved events use different condition labels; re-detecting.")
    events = utils.find_events(df)
    pd.to_pickle(events, events_file)
    return events


participants = sorted({
    f.name.split("_")[0]
    for sig in SIGNALS if Path(cfg.CLEANED_DIRS[sig]).exists()
    for f in Path(cfg.CLEANED_DIRS[sig]).glob(f"*_{sig}_cleaned.csv")
})
if not participants:
    raise SystemExit("No cleaned files found. Run the 01_ scripts first.")

for label in participants:
    print(f"Processing {label}...")
    cleaned = {}
    for signal in SIGNALS:
        try:
            cleaned[signal] = load_cleaned_signal(label, signal)
        except FileNotFoundError:
            print(f"  no cleaned {signal} file, skipping {signal}.")
    try:
        events = get_events(label, next(iter(cleaned.values())))
    except Exception as e:
        print(f"  could not get events: {e}")
        continue

    for signal, signal_df in cleaned.items():
        # cleaned CSVs don't store the sampling rate, so use SAMPLING_RATE from config
        epochs = utils.make_epochs(signal_df, events, signal, cfg.SAMPLING_RATE)
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


# Group-average plot for EDA only: skin conductance responses are slow and
# time-locked to events, so the averaged waveform is meaningful. Averaging raw
# ECG or respiration waveforms across trials is not (beats and breaths don't
# line up across trials), so those use the per-trial results instead.
plot_average_epochs("EDA", "Average electrodermal activity (EDA) across conditions")
