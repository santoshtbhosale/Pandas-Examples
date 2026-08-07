# Water Demand Excel Template

Place the master workbook here:

`WaterDemand_Template.xlsx`

The application loads this file and populates data cells only — all formatting, borders, merged cells, fonts, and layout remain unchanged.

If the template is missing, Excel export falls back to the programmatic workbook generator in `water_demand_app/services/excel_exporter.py`.

## Expected sheet names

- `Cover`
- `Consolidated`
- `Plot-A Demand`, `Plot-B Demand`
- `Plot-A UGT-OHT`, `Plot-B UGT-OHT`
- `Plot-A STP`, `Plot-B STP`
- `Summary`
