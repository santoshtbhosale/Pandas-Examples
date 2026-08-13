# American Edge Engineers — Water Demand & RWH App

Python desktop application (CustomTkinter) for engineering reports.

## Modules

1. **Water Demand Report Generator** — NBC-2026 calculations, 8-page PDF, Excel, SQLite
2. **Rain Water Harvesting** — catchment harvest & tank sizing (separate GUI / DB table / PDF)

## Run

```bash
pip install -r requirements.txt
python main.py
```

## Rain Water Harvesting

Sidebar → **Rain Water Harvesting**

- Catchment surfaces with runoff coefficients
- Annual harvest: `Area (m²) × Rainfall (mm) × K × Efficiency`
- Recommended tank = annual harvest ÷ rainy days
- Saves to SQLite table `rwh_projects` (same DB file, separate table)
- Exports its own PDF report

Package sources: `water_demand_app/rwh/` and `water_demand_app/ui/pages/rwh_page.py`

## Tests

```bash
python -m unittest water_demand_app.tests.test_calculator -v
python -m unittest water_demand_app.tests.test_rwh -v
```
