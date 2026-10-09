"""
make_example_data.py — create simulated recordings for trying out the pipeline.

Writes 4 fake participants (101–104) to ./example_data/Data/Physiology/Raw/ as
CSV files with the same channel and trigger names as the lab's BIOPAC files.
Each recording has 12 trials (4 Control, 4 Down, 4 Up). Skin conductance
responses are built in so the conditions differ: bigger after Up, smaller
after Down, none after Control.

This is SIMULATED data — useful for learning the pipeline, not for analysis.
You don't normally run this yourself:  python run_pipeline.py --demo  calls it.
"""
import os

os.environ["NK_DEMO"] = "1"   # use demo paths from config.py

from pathlib import Path

import neurokit2 as nk
import numpy as np
import pandas as pd

import config as cfg

PARTICIPANTS = ["101", "102", "103", "104"]
DURATION_S = 200
TRIAL_SPACING_S = 15
FIRST_TRIAL_S = 10
SCR_AMPLITUDE = {"ControlEvent": 0.0, "DownEvent": 0.4, "UpEvent": 1.0}  # microsiemens


def scr_kernel(sr, amplitude):
    """Simple skin conductance response shape: fast rise, slow decay (~10 s)."""
    t = np.arange(0, 10, 1 / sr)
    shape = (1 - np.exp(-t / 0.75)) * np.exp(-t / 2.0)
    return amplitude * shape / shape.max()


def make_participant(pid, sr):
    seed = int(pid)
    rng = np.random.default_rng(seed)
    n = DURATION_S * sr
    raw_names = {v: k for k, v in cfg.CHANNEL_RENAME.items()}  # short -> raw channel name

    ecg = nk.ecg_simulate(duration=DURATION_S, sampling_rate=sr,
                          heart_rate=rng.uniform(62, 78), random_state=seed)
    rsp = nk.rsp_simulate(duration=DURATION_S, sampling_rate=sr,
                          respiratory_rate=rng.uniform(12, 16), random_state=seed)
    eda = nk.eda_simulate(duration=DURATION_S, sampling_rate=sr, scr_number=0,
                          drift=-0.01, noise=0.01, random_state=seed)[:n]
    eda = np.asarray(eda) + 2.0

    triggers = {col: np.zeros(n) for col in cfg.EVENT_COLUMNS}
    order = rng.permutation(np.repeat(cfg.EVENT_COLUMNS, 4))
    for i, col in enumerate(order):
        onset = int((FIRST_TRIAL_S + i * TRIAL_SPACING_S) * sr)
        triggers[col][onset: onset + int(0.1 * sr)] = 5.0       # 100 ms, 5 V trigger pulse
        latency = onset + int(rng.uniform(1.5, 3.0) * sr)      # SCR starts 1.5–3 s after onset
        kernel = scr_kernel(sr, SCR_AMPLITUDE[col] * rng.uniform(0.7, 1.3))
        end = min(n, latency + len(kernel))
        eda[latency:end] += kernel[: end - latency]

    df = pd.DataFrame({
        raw_names.get("ECG", "ECG"): ecg[:n],
        raw_names.get("EDA", "EDA"): eda,
        raw_names.get("RSP", "RSP"): rsp[:n],
        **triggers,
    })
    return df.round(5)


def main():
    out_dir = Path(cfg.RAW_DATA_PATH)
    out_dir.mkdir(parents=True, exist_ok=True)
    for pid in PARTICIPANTS:
        path = out_dir / f"{pid}_example.csv"
        make_participant(pid, cfg.SAMPLING_RATE).to_csv(path, index=False)
        print(f"Wrote {path}")
    print(f"\nExample data ready in {out_dir}  ({cfg.SAMPLING_RATE} Hz, {DURATION_S} s each)")


if __name__ == "__main__":
    main()
