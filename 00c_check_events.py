# %%
"""
00c_check_events.py — check that events are found and labelled correctly.

Run this on one participant before the main pipeline, and whenever you use a
new dataset or change EVENT_CHANNELS / EVENT_DURATION_MODE. It shows:
  - whether the signal and trigger channels in your config exist in the file
  - every event found: time, how long its channel stayed on, condition label
  - events where more than one trigger channel was on at the same time
  - trials per condition and typical event durations
  - the epoch each signal will use, in plain words

Usage:
    python 00c_check_events.py            # uses TEST_PARTICIPANT from config
    python 00c_check_events.py 012        # any participant ID
"""
import sys

import numpy as np

import config as cfg
import utils

participant_id = sys.argv[1] if len(sys.argv) > 1 else cfg.TEST_PARTICIPANT
raw_file = utils.find_raw_file(participant_id)
if raw_file is None:
    raise SystemExit(f"No raw file for participant {participant_id} in {cfg.RAW_DATA_PATH}")

data, sr = utils.load_raw_data(raw_file)
print(f"File: {raw_file.name}   sampling rate: {sr} Hz   length: {len(data) / sr:.0f} s\n")

# ---- 1. Channels present? ----
missing_events = [c for c in cfg.EVENT_COLUMNS if c not in data.columns]
missing_signals = [c for c in cfg.CLEANED_DIRS if c not in data.columns]
if missing_signals:
    print(f"Note: signal channel(s) {missing_signals} not in this file "
          "(fine if you don't record them; otherwise check CHANNEL_RENAME).")
if missing_events:
    print(f"Missing event channel(s): {missing_events}")
    print(f"Columns in file: {data.columns.tolist()}")
    raise SystemExit("Fix EVENT_CHANNELS (or CHANNEL_RENAME) in your config_local.py.")

print("Event channels -> condition labels:")
for channel, condition in cfg.EVENT_CHANNELS.items():
    print(f"  {channel:<20} -> '{condition}'")

# ---- 2. Every event ----
events = utils.find_events(data)
n = len(events["onset"])
print(f"\n{n} events found (channel counted as ON when above {cfg.EVENT_THRESHOLD}).\n")
if n == 0:
    raise SystemExit("No events found. Check EVENT_CHANNELS and EVENT_THRESHOLD "
                     f"(max value per channel: {data[cfg.EVENT_COLUMNS].max().to_dict()}).")

print(f"{'trial':>5}  {'time (s)':>9}  {'on for (s)':>10}  {'condition':<15} note")
overlaps = 0
for i in range(n):
    onset, dur, cond = events["onset"][i], events["duration"][i], events["condition"][i]
    others = [ch for ch, c in cfg.EVENT_CHANNELS.items()
              if c != cond and data[ch].iloc[onset] > cfg.EVENT_THRESHOLD]
    note = f"OVERLAPS with {', '.join(others)}" if others else ""
    overlaps += bool(others)
    print(f"{i + 1:>5}  {onset / sr:9.2f}  {dur / sr:10.3f}  {cond:<15} {note}")

# ---- 3. Summary ----
print("\nPer condition:")
print(f"  {'condition':<15} {'trials':>6}  {'on for (s): min / median / max':>32}")
for cond in cfg.EVENT_CHANNELS.values():
    d = np.array([events["duration"][i] for i in range(n) if events["condition"][i] == cond]) / sr
    if len(d):
        print(f"  {cond:<15} {len(d):>6}  {d.min():12.3f} / {np.median(d):.3f} / {d.max():.3f}")
    else:
        print(f"  {cond:<15} {0:>6}  (no events - is this channel used?)")

if overlaps:
    print(f"\n{overlaps} event(s) start while another trigger channel is ON. Check this is "
          "intended; if not, look at those trigger channels in the raw file.")
print("\nCheck the trial counts and the order of conditions match your experiment log.")

# ---- 4. Epochs in words ----
durs = events["duration"] / sr
print(f"\nEVENT_DURATION_MODE = '{cfg.EVENT_DURATION_MODE}'")
if cfg.EVENT_DURATION_MODE == "fixed" and durs.max() > 1:
    print("  Note: channels stay ON for over 1 s. If each ON period is a whole trial or block, "
          "consider EVENT_DURATION_MODE = 'channel'.")
if cfg.EVENT_DURATION_MODE == "channel" and np.median(durs) < 0.5:
    print("  Warning: channels are only ON for short pulses, so epochs will be very short. "
          "For pulse triggers use EVENT_DURATION_MODE = 'fixed'.")

print("Epochs:")
for sig, w in cfg.EPOCH_WINDOWS.items():
    start = (f"{abs(w['start'])} s BEFORE onset" if w["start"] < 0 else
             "AT onset" if w["start"] == 0 else f"{w['start']} s AFTER onset")
    if cfg.EVENT_DURATION_MODE == "fixed":
        end = f"{w['end']} s after onset (every epoch {w['end'] - w['start']:g} s long)"
    else:
        lengths = durs + w["end"] - w["start"]
        end = (f"{w['end']} s after the channel switches OFF "
               f"(epochs {lengths.min():.1f}-{lengths.max():.1f} s long)")
    print(f"  {sig}: starts {start}, ends {end}")
