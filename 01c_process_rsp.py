# %%
"""
01c_process_rsp.py — clean RSP and run event-related RSP analysis for all participants.

Input : raw files in RAW_DATA_PATH
Output: CLEANED_DIRS["RSP"]/sub-XXX_RSP_cleaned.csv   (one per participant)
        COMBINED_FILES["RSP"]                          (one row per participant x trial)
        LOG_PATH/log_rsp.txt                           (skipped / failed participants)

All paths and settings live in config.py.
"""
from pathlib import Path

import neurokit2 as nk
import pandas as pd

import config as cfg
import utils

SIGNAL = "RSP"

# ==============================
# Setup
# ==============================
cleaned_dir = Path(cfg.CLEANED_DIRS[SIGNAL])
combined_file = Path(cfg.COMBINED_FILES[SIGNAL])
cleaned_dir.mkdir(parents=True, exist_ok=True)
combined_file.parent.mkdir(parents=True, exist_ok=True)
log = utils.Logger("rsp")

combined_df = utils.load_combined(combined_file)
processed = utils.processed_ids(combined_df)

# ==============================
# Main participant loop
# ==============================
log.start("RSP processing")

for raw_file in utils.list_raw_files():
    participant_id = utils.participant_id_from_filename(raw_file.name)
    label = utils.participant_label(participant_id)

    try:
        # ---- Exclusions / already processed ----
        if participant_id in cfg.EXCLUDED_PARTICIPANTS:
            log(f"{label} skipped: excluded.")
            continue

        if participant_id in processed:
            if not cfg.RERUN_PROCESSED_PARTICIPANTS:
                log(f"{label} skipped: already processed.")
                continue
            log(f"{label} rerun: previous results removed.")
            combined_df = combined_df[combined_df["participant_id"] != label]
            combined_df.to_csv(combined_file, index=False)

        print(f"Processing {label}...")

        # ---- Load, events, cleaning ----
        data, sampling_rate = utils.load_raw_data(raw_file)
        events = utils.find_events(data)
        data_clean, info = nk.bio_process(
            rsp=data[SIGNAL], keep=data[cfg.EVENT_COLUMNS], sampling_rate=sampling_rate
        )
        data_clean.to_csv(cleaned_dir / f"{label}_{SIGNAL}_cleaned.csv", index=False)

        # ---- Epoch + event-related analysis ----
        epochs = utils.make_epochs(data_clean, events, SIGNAL, sampling_rate)
        results = nk.rsp_analyze(epochs, sampling_rate=sampling_rate, method="event-related")
        results = utils.tidy_results(results, label)

        # ---- Append + save after every participant (safe to interrupt) ----
        combined_df = pd.concat([combined_df, results], ignore_index=True)
        combined_df.to_csv(combined_file, index=False)
        processed.add(participant_id)
        print(f"{label} processed and saved.")

    except Exception as e:
        log(f"{label} skipped: error during processing. Details: {e}")

log.finish("RSP processing")
print(f"RSP processing complete. Results: {combined_file}")
