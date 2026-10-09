# %%
"""
00b_single_subject_eda.py — OPTIONAL test run of the EDA pipeline on one participant.

Use this to check that a new dataset loads, channels are named correctly and
events are found, before running the full 01_ scripts. Shows plots and saves
one results CSV. Participant is set by TEST_PARTICIPANT in config.py.

Output: SINGLE_SUBJECT_OUTPUT_PATH/sub-XXX_eda_results.csv
"""
from pathlib import Path

import matplotlib.pyplot as plt
import neurokit2 as nk

import config as cfg
import utils

participant_id = cfg.TEST_PARTICIPANT
raw_file = utils.find_raw_file(participant_id)
if raw_file is None:
    raise FileNotFoundError(f"No raw file for participant {participant_id} in {cfg.RAW_DATA_PATH}")

# Load data (channels are renamed using CHANNEL_RENAME in config.py)
data, sampling_rate = utils.load_raw_data(raw_file)
print(f"Channels after renaming: {data.columns.tolist()}")

# Find events and plot where they fall
events = utils.find_events(data)
nk.events_plot(events, data[["EDA"]])
plt.show()

# Clean + process EDA, and visualise
data_clean, info = nk.bio_process(eda=data["EDA"], keep=data[cfg.EVENT_COLUMNS],
                                  sampling_rate=sampling_rate)
nk.eda_plot(data_clean, info)
plt.show()

# Epoch + event-related analysis
epochs = utils.make_epochs(data_clean, events, "EDA", sampling_rate)
results = nk.eda_analyze(epochs, sampling_rate=sampling_rate, method="event-related")
results = utils.tidy_results(results, utils.participant_label(participant_id))
print(results)

out_dir = Path(cfg.SINGLE_SUBJECT_OUTPUT_PATH)
out_dir.mkdir(parents=True, exist_ok=True)
results.to_csv(out_dir / f"sub-{participant_id}_eda_results.csv", index=False)
