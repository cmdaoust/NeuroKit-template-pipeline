# %%
"""
02_qa_plots.py — interactive raw-vs-cleaned QA plots with event markers.

For every participant with cleaned data, saves one HTML plot per signal:
  top panel    = raw signal
  bottom panel = cleaned signal, with a marker + solid grey line at each event
                 onset and a dotted line where its epoch ends (set by
                 EPOCH_WINDOWS and EVENT_DURATION_MODE).

Use these to spot noisy segments. Bad ECG samples can be listed in
MANUAL_REJECTION_FILE and 01a_process_ecg.py re-run with masking.

Requires: 01a/01b/01c to have been run.
Input : RAW_DATA_PATH, CLEANED_DIRS
Output: QA_PLOTS_PATH/sub-XXX/sub-XXX_<SIGNAL>_QA_epochs.html
"""
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import config as cfg
import utils

SIGNALS = ["RSP", "EDA", "ECG"]
DS = cfg.DOWNSAMPLE_FACTOR


def vertical_lines(xs, y_min, y_max):
    """x/y lists drawing many vertical lines as ONE trace (fast)."""
    x_line, y_line = [], []
    for x in xs:
        x_line += [x, x, None]
        y_line += [y_min, y_max, None]
    return x_line, y_line


# ==============================
# Participants = anyone with at least one cleaned file
# ==============================
participants = sorted({
    f.name.split("_")[0]
    for sig in SIGNALS if Path(cfg.CLEANED_DIRS[sig]).exists()
    for f in Path(cfg.CLEANED_DIRS[sig]).glob(f"*_{sig}_cleaned.csv")
})
if not participants:
    raise SystemExit("No cleaned files found. Run the 01_ scripts first.")

# ==============================
# Main loop
# ==============================
for label in participants:
    print(f"Plotting {label}...")
    raw_file = utils.find_raw_file(label.replace("sub-", ""))
    if raw_file is None:
        print("  Raw file missing, skipping.")
        continue

    raw_data, sampling_rate = utils.load_raw_data(raw_file)
    out_dir = Path(cfg.QA_PLOTS_PATH) / label
    out_dir.mkdir(parents=True, exist_ok=True)

    for sig in SIGNALS:
        cleaned_file = Path(cfg.CLEANED_DIRS[sig]) / f"{label}_{sig}_cleaned.csv"
        if not cleaned_file.exists():
            print(f"  {sig} cleaned file missing.")
            continue

        df_clean = pd.read_csv(cleaned_file)
        col = f"{sig}_Clean"
        if col not in df_clean.columns:
            print(f"  {col} not found.")
            continue

        raw_plot = raw_data[sig].iloc[::DS].reset_index(drop=True)
        clean_plot = df_clean[col].iloc[::DS].reset_index(drop=True)
        y_min, y_max = clean_plot.min(), clean_plot.max()

        # Events (from the trigger channels kept in the cleaned file) and epoch ends
        try:
            events = utils.find_events(df_clean)
        except KeyError as e:
            print(f"  {e} Plotting without events.")
            events = {"onset": [], "duration": [], "condition": [], "label": []}
        _, ends = utils.epoch_window(events, sig, sampling_rate)
        if not isinstance(ends, list):
            ends = [ends] * len(events["onset"])
        end_samples = [o + int(e * sampling_rate) for o, e in zip(events["onset"], ends)]

        fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                            subplot_titles=("Raw signal", "Cleaned signal"))
        fig.add_trace(go.Scatter(y=raw_plot, mode="lines", name="Raw",
                                 line=dict(color="darkcyan")), row=1, col=1)
        fig.add_trace(go.Scatter(y=clean_plot, mode="lines", name="Cleaned",
                                 line=dict(color="crimson")), row=2, col=1)

        for condition in dict.fromkeys(events["condition"]):   # one legend entry per condition
            idx = [i for i, c in enumerate(events["condition"]) if c == condition]
            onset_ds = [events["onset"][i] // DS for i in idx]
            end_ds = [end_samples[i] // DS for i in idx]

            # Hoverable marker at each event onset
            fig.add_trace(go.Scatter(x=onset_ds, y=[y_min] * len(onset_ds), mode="markers",
                                     marker=dict(symbol="line-ns-open", size=12),
                                     name=str(condition)), row=2, col=1)
            # Solid line = event onset, dotted line = epoch end
            x, y = vertical_lines(onset_ds, y_min, y_max)
            fig.add_trace(go.Scatter(x=x, y=y, mode="lines", hoverinfo="skip", showlegend=False,
                                     line=dict(color="gray", width=0.8)), row=2, col=1)
            x, y = vertical_lines(end_ds, y_min, y_max)
            fig.add_trace(go.Scatter(x=x, y=y, mode="lines", hoverinfo="skip", showlegend=False,
                                     line=dict(color="darkblue", width=0.8, dash="dot")), row=2, col=1)

        fig.update_layout(
            title=f"{label} – {sig} QA (x axis = samples / {DS})",
            height=750, hovermode="x unified",
        )
        fig.write_html(out_dir / f"{label}_{sig}_QA_epochs.html")
        print(f"  Saved {sig} QA plot.")

print(f"QA plotting complete. Plots in: {cfg.QA_PLOTS_PATH}")
