"""
run_simulations.py - solve several AEDT/HFSS projects one after another.

What it does
  For every project in PROJECTS (in order):
    1. starts a fresh, non-graphical AEDT session
    2. opens the project
    3. solves EVERYTHING in it (all designs, all setups, frequency sweeps
       and Optimetrics/parametric sweeps) - same as "Analyze All" in the GUI
    4. saves the project and closes AEDT completely (frees RAM/licences)
  If a project fails, the error is logged and the next project starts.
  Progress is written to the console and to run_simulations.log
  (in the same folder as this script).

Usage
  1. Edit the SETTINGS section below (project paths, AEDT version).
  2. Make sure none of the projects is open in the AEDT GUI.
  3. In a command prompt:  python run_simulations.py
  4. Lock the PC (Win+L) - do NOT log out, that kills the run.

Requirements
  pip install pyaedt     (or: pip install --user pyaedt)

Number of cores / HPC: taken from AEDT's own HPC settings
(Tools > Options > HPC and Analysis Options), same as in the GUI.
"""

import datetime
import os
import sys
import time

# ============================ SETTINGS =====================================

# Projects to solve, in this order. Use full paths, ideally on a local disk
# (e.g. D:\...), not in a OneDrive folder.
PROJECTS = [
    r"D:\Sims\x_offset.aedt",
    r"D:\Sims\z_offset.aedt",
    r"D:\Sims\dielectric.aedt",
]

# Installed AEDT version, e.g. "2024.2" (folder v242), "2025.1" (v251), ...
AEDT_VERSION = "2024.2"

# ===========================================================================

LOGFILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "run_simulations.log")

# PyAEDT moved its import path in version 0.9; support both.
try:
    from ansys.aedt.core import Desktop
except ImportError:
    from pyaedt import Desktop


def log(msg):
    line = f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    with open(LOGFILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def start_desktop():
    """Start a new non-graphical AEDT session (handles old/new PyAEDT)."""
    try:  # PyAEDT >= 0.9
        return Desktop(version=AEDT_VERSION, non_graphical=True,
                       new_desktop=True, close_on_exit=True)
    except TypeError:  # older PyAEDT
        return Desktop(specified_version=AEDT_VERSION, non_graphical=True,
                       new_desktop_session=True, close_on_exit=True)


def fmt_duration(seconds):
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h}h {m:02d}min {s:02d}s"


def check_projects():
    """Warn about missing files or projects that are still open/locked."""
    ok = []
    for p in PROJECTS:
        if not os.path.isfile(p):
            log(f"SKIPPED (file not found): {p}")
            continue
        if os.path.exists(p + ".lock"):
            log(f"WARNING: lock file found for {p} - is it open in the GUI? "
                f"Close it (or delete the .lock file if AEDT crashed).")
        ok.append(p)
    return ok


def solve(project_path):
    desktop = start_desktop()
    try:
        oproject = desktop.odesktop.OpenProject(project_path)
        log(f"  opened, solving all setups and sweeps ...")
        oproject.AnalyzeAll()   # all designs, setups, sweeps, Optimetrics
        oproject.Save()
        log(f"  saved")
    finally:
        desktop.release_desktop(close_projects=True, close_desktop=True)


def main():
    log("=" * 60)
    log(f"Batch run started, AEDT {AEDT_VERSION}, {len(PROJECTS)} project(s)")
    projects = check_projects()
    results = []

    for i, p in enumerate(projects, 1):
        log(f"({i}/{len(projects)}) START {p}")
        t0 = time.time()
        try:
            solve(p)
            status = "OK"
        except Exception as e:  # keep going with the next project
            status = f"FAILED: {e!r}"
        dt = fmt_duration(time.time() - t0)
        log(f"({i}/{len(projects)}) {status} after {dt}: {p}")
        results.append((p, status, dt))

    log("-" * 60)
    log("Summary:")
    for p, status, dt in results:
        log(f"  {status:<8.8} {dt:>16}  {os.path.basename(p)}")
    log("Batch run finished")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("Stopped by user (Ctrl+C)")
        sys.exit(1)