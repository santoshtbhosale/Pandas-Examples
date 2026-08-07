# Water Demand Excel Template

Place the master workbook here:

`WaterDemand_Template.xlsx`

The application copies this file and populates data cells only. All formatting, merged cells, borders, fonts, formulas, and print settings remain unchanged.

Optional reference document:

`Comments.docx` — engineering comments, UI rules, NBC tables, and screenshot requirements.

If the template is missing, Excel export falls back to the programmatic workbook generator in `water_demand_app/services/excel_exporter.py`.

## Expected sheet names

- `Cover`
- `Consolidated`
- `Plot-A Demand`, `Plot-B Demand`
- `Plot-A UGT-OHT`, `Plot-B UGT-OHT`
- `Plot-A STP`, `Plot-B STP`
- `Summary`
