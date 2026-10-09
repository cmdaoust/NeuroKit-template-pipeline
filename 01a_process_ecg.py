# %%
"""
01a_process_ecg.py — clean ECG, run event-related ECG analysis and compute HRV
for all participants.

Input : raw files in RAW_DATA_PATH
        (optional) MANUAL_REJECTION_FILE listing bad ECG samples
Output: CLEANED_DIRS["ECG"]/sub-XXX_ECG_cleaned.csv   (one per participant)
        COMBINED_FILES["ECG"]                          (one row per participant x trial;
                                                        includes per-epoch HRV for long epochs)
        HRV_FILE                                       (whole-recording HRV, one row per participant)
        LOG_PATH/log_ecg.txt                           (skipped / failed participants)

All paths and settings live in config.py.
"""
from pathlib import Path

import neurokit2 as nk
import numpy as np
import pandas as pd

import config as cfg
import utils

SIGNAL = "ECG"

# ==============================
# Setup
# ==============================
cleaned_dir = Path(cfg.CLEANED_DIRS[SIGNAL])
combined_file = Path(cfg.COMBINED_FILES[SIGNAL])
cleaned_dir.mkdir(parents=True, exist_ok=True)
combined_file.parent.mkdir(parents=True, exist_ok=True)
log = utils.Logger("ecg")

# Optional list of bad ECG samples from manual inspection
if cfg.MANUAL_REJECTION_FILE and Path(cfg.MANUAL_REJECTION_FILE).exists():
    # keep_default_na=False so a literal "NA" stays a string (pandas would otherwise turn it into NaN)
    bad_events_df = pd.read_csv(cfg.MANUAL_REJECTION_FILE, dtype=str, keep_default_na=False)
else:
    bad_events_df = pd.DataFrame(columns=["participant", "signal", "onset_sample"])
    print("No manual rejection file found: ECG will not be masked.")

combined_df = utils.load_combined(combined_file)
processed = utils.processed_ids(combined_df)
hrv_df = utils.load_combined(cfg.HRV_FILE)

# ==============================
# Main participant loop
# ==============================
log.start("ECG processing")

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
            if not hrv_df.empty:
                hrv_df = hrv_df[hrv_df["participant_id"] != label]
                hrv_df.to_csv(cfg.HRV_FILE, index=False)

        # ---- Manually flagged bad segments ----
        participant_bad = bad_events_df[
            (bad_events_df["participant"] == label) & (bad_events_df["signal"] == SIGNAL)
        ]
        # An onset_sample of "NA" marks the whole ECG recording as unusable
        if participant_bad["onset_sample"].astype(str).str.strip().str.upper().eq("NA").any():
            log(f"{label} skipped: onset_sample contains 'NA' (ECG unusable).")
            continue

        print(f"Processing {label}...")

        # ---- Load ----
        data, sampling_rate = utils.load_raw_data(raw_file)
        ecg = data[SIGNAL].copy().astype(float)

        # ---- Mask bad segments (NeuroKit interpolates over NaNs when cleaning) ----
        if not participant_bad.empty and cfg.ECG_BAD_WINDOW_SEC > 0:
            half_window = int(cfg.ECG_BAD_WINDOW_SEC * sampling_rate)
            for onset in participant_bad["onset_sample"].astype(int):
                ecg.iloc[max(0, onset - half_window): min(len(ecg), onset + half_window)] = np.nan
            print(f"{label}: masked {len(participant_bad)} ECG segments "
                  f"({ecg.isna().mean() * 100:.2f}% of signal)")

        # ---- Events, cleaning ----
        events = utils.find_events(data)
        data_clean, info = nk.bio_process(
            ecg=ecg, keep=data[cfg.EVENT_COLUMNS], sampling_rate=sampling_rate
        )
        data_clean.to_csv(cleaned_dir / f"{label}_{SIGNAL}_cleaned.csv", index=False)

        # ---- Epoch + event-related analysis ----
        epochs = utils.make_epochs(data_clean, events, SIGNAL, sampling_rate)
        results = nk.ecg_analyze(epochs, sampling_rate=sampling_rate, method="event-related")
        results = utils.tidy_results(results, label)

        # ---- HRV ----
        if cfg.HRV_WHOLE_RECORDING or cfg.HRV_PER_EPOCH:
            peaks = utils.hrv_peaks(data_clean["ECG_Clean"], sampling_rate)
        if cfg.HRV_PER_EPOCH:
            epoch_hrv = utils.hrv_per_epoch(peaks, events, sampling_rate)
            if epoch_hrv is not None:   # only epochs >= HRV_MIN_EPOCH_SEC get values
                results["Trial"] = results["Trial"].astype(str)
                results = results.merge(epoch_hrv, left_on="Trial", right_index=True, how="left")
        if cfg.HRV_WHOLE_RECORDING:
            try:
                if not hrv_df.empty:
                    hrv_df = hrv_df[hrv_df["participant_id"] != label]
                hrv_df = pd.concat([hrv_df, utils.hrv_whole(peaks, sampling_rate, label)],
                                   ignore_index=True)
                hrv_df.to_csv(cfg.HRV_FILE, index=False)
            except Exception as e:      # HRV failing shouldn't lose the ECG results
                log(f"{label}: whole-recording HRV failed. Details: {e}")

        # ---- Append + save after every participant (safe to interrupt) ----
        combined_df = pd.concat([combined_df, results], ignore_index=True)
        combined_df.to_csv(combined_file, index=False)
        processed.add(participant_id)
        print(f"{label} processed and saved.")

    except Exception as e:
        log(f"{label} skipped: error during processing. Details: {e}")

log.finish("ECG processing")
print(f"ECG processing complete. Results: {combined_file}")
if cfg.HRV_WHOLE_RECORDING:
    print(f"Whole-recording HRV: {cfg.HRV_FILE}")
