# PlanetCode Engineering Suite v2.0.0

American Edge Engineers — Water Demand & Rain Water Harvesting desktop application.

## Requirements

- Python 3.10+
- See `requirements.txt`

## Install

```bash
pip install -r requirements.txt
```

## Run from source (recommended)

```bash
cd water_demand_app
python main.py
```

Alternative bundled single-file mode:

```bash
python build_main.py
python main.py
```

## Default logins

| Role | Username | Password |
|------|----------|----------|
| Super Admin | superadmin | Super@123 |
| Admin | admin | Admin@123 |
| Team Leader | leader | Leader@123 |
| Engineer | akash | Akash@123 |
| Viewer | omkar | Omkar@123 |

## Features (v2.0)

- Role-based login (Super Admin, Admin, Team Leader, Engineer, Viewer)
- Team Leader dashboard with project assignment and engineer performance
- Engineer dashboard with project timer (elapsed, remaining, delay)
- Project workflow: assign, pause/resume, complete, audit log
- NBC-2026 water demand calculations with live auto-calc
- Dynamic project-type tabs
- PDF and Excel export (template: `templates/WaterDemand_Template.xlsx`)
- SQLite project database with auto project ID
- Rain Water Harvesting module

## Tests

```bash
python -m unittest discover -s water_demand_app/tests -v
```

Expected: **88/88 tests passing**

## Build executable

```bash
python build_exe.py
```

Output: `dist/PlanetCode_Engineering_Suite_V2.0` (Linux/macOS) or `dist/PlanetCode_Engineering_Suite_V2.0.exe` (Windows)

## Project structure

```
water_demand_app/     # Application source (modular)
  config/             # NBC rules, page visibility
  models/             # Data models
  services/           # Calculator, DB, auth, audit, workflow
  ui/                 # Screens and pages
  rwh/                # Rain water harvesting module
  tests/              # Unit tests (88)
templates/            # Excel template
logo.png              # Company logo
footer_banner.png     # PDF footer
build_main.py         # Bundle to main.py
build_exe.py          # PyInstaller production build
requirements.txt
VERSION               # 2.0.0
```

## Reference files

- `templates/WaterDemand_Template.xlsx` — Excel master template
- `templates/Comments.docx` — engineering reference (when provided)

## Version

**PlanetCode Engineering Suite v2.0.0**
