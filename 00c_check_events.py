# %%
"""
00c_check_events.py — check that events are found and labelled correctly.

Run this on one participant before the main pipeline (and whenever you change
EVENT_COLUMNS or use a new dataset). For every detected event it checks which
trigger channel is actually active at that moment and compares it with the
condition label the pipeline will assign. It also prints each epoch window
in plain words.

Usage:
    python 00c_check_events.py            # uses TEST_PARTICIPANT from config
    python 00c_check_events.py 012        # any participant ID
"""
import sys

import config as cfg
import utils

participant_id = sys.argv[1] if len(sys.argv) > 1 else cfg.TEST_PARTICIPANT
raw_file = utils.find_raw_file(participant_id)
if raw_file is None:
    raise SystemExit(f"No raw file for participant {participant_id} in {cfg.RAW_DATA_PATH}")

data, sampling_rate = utils.load_raw_data(raw_file)
print(f"File: {raw_file.name}   sampling rate: {sampling_rate} Hz\n")

# ---- 1. Channels present? ----
missing = [c for c in cfg.EVENT_COLUMNS + ["ECG", "EDA", "RSP"] if c not in data.columns]
if missing:
    print(f"Missing channels: {missing}")
    print(f"Columns in file: {data.columns.tolist()}")
    raise SystemExit("Fix CHANNEL_RENAME / EVENT_COLUMNS in your config_local.py.")

# ---- 2. Code -> label mapping ----
print("Condition codes (from the order of EVENT_COLUMNS):")
for i, col in enumerate(cfg.EVENT_COLUMNS):
    code = 2 ** i
    print(f"  {col:<15} -> code {code} -> label '{cfg.CONDITION_LABELS.get(code, '???')}'")

# ---- 3. Check every event against the channel that is actually active ----
events = utils.find_events(data)
print(f"\n{len(events['onset'])} events found.\n")
print(f"{'time (s)':>9}  {'code':>4}  {'label':<10} {'active channel(s)':<25} ok?")

problems = 0
for onset, code in zip(events["onset"], events["condition"]):
    active = [c for c in cfg.EVENT_COLUMNS if data[c].iloc[onset] > cfg.EVENT_THRESHOLD]
    label = cfg.CONDITION_LABELS.get(code, "???")
    # The code should be 2**(position of the active channel in EVENT_COLUMNS)
    ok = len(active) == 1 and code == 2 ** cfg.EVENT_COLUMNS.index(active[0])
    problems += not ok
    print(f"{onset / sampling_rate:9.1f}  {code:>4}  {label:<10} {', '.join(active) or '-':<25} "
          f"{'yes' if ok else 'NO'}")

labels = [cfg.CONDITION_LABELS.get(code, code) for code in events["condition"]]
print(f"\nTrials per condition: { {lab: labels.count(lab) for lab in dict.fromkeys(labels)} }")

if problems:
    print(f"\n{problems} event(s) did NOT match. Overlapping triggers or a label mapping that "
          "doesn't follow the channel order are the usual causes.")
else:
    print("\nAll event labels match the active trigger channel.")
print("Also check the labels match what you know about the task "
      "(e.g. the block order in your experiment log).")

# ---- 4. Epoch windows in words ----
print("\nEpoch windows:")
for sig, w in cfg.EPOCH_WINDOWS.items():
    start = (f"{abs(w['start'])} s BEFORE" if w["start"] < 0 else
             "AT" if w["start"] == 0 else f"{w['start']} s AFTER")
    print(f"  {sig}: starts {start} event onset, ends {w['end']} s after onset")
