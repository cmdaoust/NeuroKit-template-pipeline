# Getting started (no coding experience needed)

This guide takes you from nothing installed to processed results. It takes about
**30 minutes the first time**. After that, a run takes four commands
(see [Every time you use it](#every-time-you-use-it)).

You'll type commands into a **terminal**, a window where you type instructions instead
of clicking. Copy each command from this page, paste it in, and press **Enter**.

---

## Part 1 — One-time setup

### Step 1. Download the pipeline

1. Open the repository page on GitHub (ask whoever shared it for the link and for access).
2. Click the green **Code** button → **Download ZIP**.
3. Unzip it and move the folder somewhere sensible, for example `Documents/NeuroKit-template-pipeline`.

### Step 2. Install Miniconda (gives you Python)

1. Go to <https://www.anaconda.com/docs/getting-started/miniconda> and download the **Miniconda**
   graphical installer for your computer (`.pkg` for Mac, `.exe` for Windows).
   - Mac: choose **Apple Silicon** for M1/M2/M3/M4 Macs, or **Intel** for older Macs
     (Apple menu → About This Mac shows which you have).
2. Run the installer and accept the defaults.

### Step 3. Open a terminal

- **Mac:** open **Terminal** (press Cmd + Space and type *Terminal*).
- **Windows:** open **Anaconda Prompt** from the Start menu. Don't use the ordinary
  Command Prompt, because it can't find conda.

To check it worked, type this and press Enter:
```
conda --version
```
You should see something like `conda 25.x`. If you get *"command not found"*, close the terminal,
open a new one and try again.

### Step 4. Go to the pipeline folder

Type `cd ` (with a space after it), **drag the pipeline folder from Finder/File Explorer into
the terminal window** so its path appears, then press Enter.
```
cd /Users/yourname/Documents/NeuroKit-template-pipeline
```

### Step 5. Install the packages the pipeline needs

```
conda env create -f environment.yml
```
This downloads everything the pipeline needs and takes 5–10 minutes. You only do it once.

### Step 6. Check everything works using example data

```
conda activate neurokit-pipeline
python run_pipeline.py --demo
```
This makes four fake participants and runs the whole pipeline on them. When it says
**`Pipeline finished.`**, open the `example_data/Data` folder inside the pipeline folder:

- `Figures/QA_Plots/` holds interactive plots. Double-click a `.html` file to open it in your browser.
- `Figures/` also holds the average-response plots.
- `Combined/` holds the results tables (`.csv`), which open in Excel.

If that worked, your setup is complete.

---

## Part 2 — Set it up for your data

### Step 7. Install Box Drive and organise your data in Box

Our data live in **Box**. With **Box Drive**, your Box folders appear on your computer like
normal folders, but the files stay in Box. They're only downloaded when the pipeline opens them,
so you don't need space on your computer for large data files, and results are saved back to Box.

1. Install **Box Drive** (from the university software page or <https://www.box.com/drive>) and
   sign in with your university account.
2. Check it works: on a Mac, **Box** appears under *Locations* in the Finder sidebar. On Windows,
   a **Box** folder appears in File Explorer.

In Box, put your raw AcqKnowledge files in a folder structure like this:
```
MyStudy/
└── Data/
    └── Physiology/
        └── Raw/
            ├── 008_filtered_chopped.acq
            ├── 009_filtered_chopped.acq
            └── ...
```
- Each filename must **start with the 3-digit participant number** (`008`, `012`, …).
- `MyStudy` can be any folder name you like, anywhere in Box.
- Results will be saved into this same `Data` folder in Box.

### Step 8. Create your settings file

1. In the pipeline folder, make a **copy** of `config_local.example.py`.
2. Rename the copy to exactly **`config_local.py`**.
   - **Windows:** turn on *View → Show → File name extensions* first. Otherwise you can end up
     with `config_local.py.txt` without noticing.
3. Open `config_local.py` in a plain-text editor:
   - Mac: right-click → Open With → **TextEdit**. If TextEdit shows formatting options, choose
     Format → **Make Plain Text**.
   - Windows: right-click → Open with → **Notepad**.
   - Or install [VS Code](https://code.visualstudio.com/) (free), which is nicer for this.

### Step 9. Fill in your settings

Change the `PROJECT_ROOT = ...` line to the path of your `MyStudy` folder in Box.

**Getting the path:**
- **Mac:** in Finder, open **Box** in the sidebar, find your study folder, right-click it,
  hold **Option**, and choose **Copy "MyStudy" as Pathname**. Paste it between the quotes.
  It will look like `/Users/jo/Library/CloudStorage/Box-Box/MyLab/MyStudy`.
- **Windows:** in File Explorer, Shift + right-click the folder → **Copy as path**.

> ⚠️ **Windows users:** change every backslash `\` in the path to a forward slash `/`,
> e.g. `"C:/Users/jo/Box/MyLab/MyStudy"`. Backslashes cause an error.

Your file should end up looking like this:
```python
PROJECT_ROOT = "/Users/jo/Library/CloudStorage/Box-Box/MyLab/MyStudy"

EXCLUDED_PARTICIPANTS = {"003", "017"}    # participants to skip, or set() for none

TEST_PARTICIPANT = "008"                   # a participant with good data, used for checks

# Your trigger channels: "name of the channel in your data": "condition label"
EVENT_CHANNELS = {"ControlEvent": "Control", "DownEvent": "Down", "UpEvent": "Up"}
```
Keep the quote marks, colons, commas and curly brackets exactly as shown. Save the file.

**Trigger channels.** List each trigger (event marker) channel in your recordings and the condition
it marks. You can have one channel or several. If you're not sure what your channels are called,
run Step 10. It lists the channel names in your file when it can't find the ones you gave.

**Short triggers or whole blocks?** By default, each trigger marks the *start* of a trial, and every
trial is analysed over the same time window. If instead your trigger channel stays **on for the
whole block** (for example, a 2-minute task block), and you want each block analysed from start to
end, add this line:
```python
EVENT_DURATION_MODE = "channel"
```
Ask whoever maintains the pipeline to help set the time windows (`EPOCH_WINDOWS`) for your study.

### Step 10. Check your events are read correctly

In the terminal (inside the pipeline folder, with `conda activate neurokit-pipeline` done):
```
python 00c_check_events.py
```
This prints a table of every event it found in your test participant. Check that:

- the **number of trials per condition** matches your experiment design,
- the **order of conditions** matches what you know happened in that session,
- the **"on for (s)"** column makes sense: short pulses (e.g. 0.1 s) for trial-start triggers,
  or the length of each block if your triggers stay on for the whole block,
- nothing is marked **OVERLAPS**, unless your design really has two triggers on at once.

If it says channels are missing, finds no events, or anything above looks wrong, ask someone who
knows the pipeline before going further.

---

## Part 3 — Run it

```
python run_pipeline.py
```
This processes every participant and takes about a minute per participant. The first run from Box
takes longer, because each raw file is downloaded as it's opened. Results are saved inside your
`MyStudy/Data` folder in Box:

| Folder | What's in it |
|---|---|
| `Data/Combined/` | **Your results:** one table per signal (`ecg_…`, `eda_…`, `rsp_…`), with one row per trial, plus `hrv_results_combined.csv` with heart rate variability for each participant. Open them in Excel, SPSS, JASP or R. |
| `Data/Figures/QA_Plots/` | One interactive plot per participant and signal. **Look through these** to check the cleaned signals look sensible. |
| `Data/Figures/` | Average response for each condition. |
| `Data/Processing/` | Log files listing any participants that were skipped, and why. |

---

## Every time you use it

Open a terminal and type:
```
cd /path/to/NeuroKit-template-pipeline
conda activate neurokit-pipeline
python run_pipeline.py
```
(For the `cd` line, drag the folder in, as in Step 4.)

**Adding new participants:** put their files in `Raw/` and run `python run_pipeline.py` again.
Participants that were already processed are skipped automatically.

**Re-processing everyone** (e.g. after changing a setting): add
`RERUN_PROCESSED_PARTICIPANTS = True` to `config_local.py`, run, then remove the line again.

---

## If something goes wrong

| You see | What to do |
|---|---|
| `conda: command not found` | Close and reopen the terminal. On Windows, make sure you opened **Anaconda Prompt**. |
| `No module named 'neurokit2'` (or pandas, plotly…) | You forgot `conda activate neurokit-pipeline`. Run it, then try again. |
| `No module named 'config'` or `can't open file` | You're not in the pipeline folder. Do the `cd` step again. |
| `PROJECT_ROOT is not set` | `config_local.py` is missing or misnamed. Check Steps 8–9 (and the Windows file-extension tip). |
| `SyntaxError` mentioning `config_local.py` | There's a typo in your settings file: a missing quote mark or bracket, or a backslash in a Windows path. |
| `RAW_DATA_PATH does not exist` | The path in `PROJECT_ROOT` is wrong, or your files aren't in `Data/Physiology/Raw/`. If your data are in Box, check that Box Drive is running and you're signed in. |
| Running is very slow | On the first run from Box, files are downloading. You need a working internet connection. |
| `PermissionError` when saving a `.csv` | The results file is open in Excel, or a colleague is running the pipeline on the same Box folder. Close it and run again. |
| `Warning: unknown setting(s) in config_local.py` | A setting name is misspelled. Compare it with `config_local.example.py`. |
| A participant is listed as *skipped: error during processing* | The other participants still run. The error message is in `Data/Processing/log_<signal>.txt`. Send it to whoever maintains the pipeline. |

When asking for help, copy the **whole** error message from the terminal (the last few lines matter most).
