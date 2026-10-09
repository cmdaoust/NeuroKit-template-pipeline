"""
run_pipeline.py — run the whole pipeline in the right order with one command.

Examples:
    python run_pipeline.py --demo          # try it on simulated example data
    python run_pipeline.py                 # run on your data (needs config_local.py)
    python run_pipeline.py --steps 02 03   # only re-run the QA plots and epochs
    python run_pipeline.py --show-plots    # open figures in windows as they're made

Steps (in order):
    00c  check events and condition labels (TEST_PARTICIPANT)
    01a  ECG cleaning + analysis
    01b  EDA cleaning + analysis
    01c  RSP cleaning + analysis
    02   QA plots
    03   epochs + group-average plots
"""
import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent
STEPS = {
    "00c": "00c_check_events.py",
    "01a": "01a_process_ecg.py",
    "01b": "01b_process_eda.py",
    "01c": "01c_process_rsp.py",
    "02": "02_qa_plots.py",
    "03": "03_epochs_and_average_plots.py",
}


def main():
    parser = argparse.ArgumentParser(description="Run the NeuroKit2 pipeline.")
    parser.add_argument("--demo", action="store_true",
                        help="use simulated example data (created automatically if missing)")
    parser.add_argument("--steps", nargs="+", choices=list(STEPS), default=list(STEPS),
                        help="which steps to run (default: all)")
    parser.add_argument("--show-plots", action="store_true",
                        help="show matplotlib figures in windows (default: just save them)")
    args = parser.parse_args()

    env = os.environ.copy()
    if not args.show_plots:
        env["MPLBACKEND"] = "Agg"     # save figures without opening windows
    if args.demo:
        env["NK_DEMO"] = "1"
        if not any((REPO_DIR / "example_data").rglob("*.csv")):
            print("== Creating example data ==")
            subprocess.run([sys.executable, "make_example_data.py"], cwd=REPO_DIR, env=env, check=True)

    for step in [s for s in STEPS if s in args.steps]:      # always run in pipeline order
        script = STEPS[step]
        print(f"\n== Step {step}: {script} ==", flush=True)
        t0 = time.time()
        result = subprocess.run([sys.executable, script], cwd=REPO_DIR, env=env)
        if result.returncode != 0:
            sys.exit(f"\nStep {step} failed (see the error above). Fix it, then re-run with "
                     f"--steps {' '.join(s for s in STEPS if s in args.steps and s >= step)}")
        print(f"== Step {step} done in {time.time() - t0:.0f} s ==")

    print("\nPipeline finished.")
    if args.demo:
        print(f"Outputs are in {REPO_DIR / 'example_data' / 'Data'}")


if __name__ == "__main__":
    main()
