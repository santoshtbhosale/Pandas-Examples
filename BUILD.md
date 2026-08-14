# Building the Windows Executable

## Prerequisites

- Python 3.10+
- Windows (for `.exe` output) or Linux/macOS (for a standalone binary)

## Quick build (Windows)

```bat
scripts\build_windows_exe.bat
```

## Quick build (Linux/macOS)

```bash
bash scripts/build_windows_exe.sh
```

## What the build does

1. Runs `water_demand_app/build_main.py` to bundle modules into `main.py`
2. Installs runtime dependencies plus PyInstaller
3. Builds a single-file windowed executable: `dist/AmericanEdge_WaterDemand.exe` (Windows) or `dist/AmericanEdge_WaterDemand` (Linux)

## Bundled assets

When present, these files are included automatically:

- `logo.png` or `water_demand_app/assets/logo.png`
- `templates/WaterDemand_Template.xlsx`

## Development entry point

For day-to-day development, run the modular app directly:

```bash
cd water_demand_app
python app_launcher.py
```

## Database backups

The application automatically backs up the SQLite database to `data/backups/` on save and exit. Manual backup/restore is available under **Settings** in the project workflow.
