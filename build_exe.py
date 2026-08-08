#!/usr/bin/env python3
"""Build PlanetCode Engineering Suite V2.0 production executable."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(ROOT, "water_demand_app")
DIST = os.path.join(ROOT, "dist")
BUILD = os.path.join(ROOT, "build")
EXE_NAME = "PlanetCode_Engineering_Suite_V2.0"
ENTRY = os.path.join(APP, "main.py")


def main() -> int:
  subprocess.check_call([sys.executable, os.path.join(ROOT, "build_main.py")])

  try:
    import PyInstaller  # noqa: F401
  except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller", "-q"])

  sep = ";" if os.name == "nt" else ":"
  add_data = [
    f"{os.path.join(ROOT, 'templates')}{sep}templates",
    f"{os.path.join(ROOT, 'logo.png')}{sep}.",
    f"{os.path.join(ROOT, 'footer_banner.png')}{sep}.",
    f"{os.path.join(APP, 'assets', 'logo.png')}{sep}assets",
  ]

  cmd = [
    sys.executable,
    "-m",
    "PyInstaller",
    "--noconfirm",
    "--clean",
    "--onefile",
    "--windowed",
    f"--name={EXE_NAME}",
    f"--distpath={DIST}",
    f"--workpath={BUILD}",
    f"--specpath={ROOT}",
    f"--paths={APP}",
    "--collect-all",
    "customtkinter",
    "--collect-all",
    "tkcalendar",
  ]
  for item in add_data:
    cmd.extend(["--add-data", item])
  cmd.append(ENTRY)

  print("Building executable:", EXE_NAME)
  subprocess.check_call(cmd, cwd=ROOT)

  built = os.path.join(DIST, EXE_NAME)
  if os.name == "nt":
    built += ".exe"
  if os.path.isfile(built):
    print("SUCCESS:", built)
    return 0
  print("Build finished but executable not found at", built)
  return 1


if __name__ == "__main__":
  raise SystemExit(main())
