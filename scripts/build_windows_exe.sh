#!/usr/bin/env bash
# Build executable bundle (Linux/macOS). For Windows .exe, run build_windows_exe.bat on Windows.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "Rebuilding main.py from source modules..."
python3 water_demand_app/build_main.py

echo "Installing build dependencies..."
pip install -r requirements.txt pyinstaller

echo "Building executable..."
ADD_DATA=()
if [[ -f "$ROOT/logo.png" ]]; then
  ADD_DATA+=(--add-data "$ROOT/logo.png:.")
fi
if [[ -f "$ROOT/water_demand_app/assets/logo.png" ]]; then
  ADD_DATA+=(--add-data "$ROOT/water_demand_app/assets/logo.png:assets")
fi
if [[ -f "$ROOT/templates/WaterDemand_Template.xlsx" ]]; then
  ADD_DATA+=(--add-data "$ROOT/templates/WaterDemand_Template.xlsx:templates")
fi

pyinstaller --noconfirm --onefile --windowed \
  --name "AmericanEdge_WaterDemand" \
  --distpath "$ROOT/dist" \
  --workpath "$ROOT/build" \
  --specpath "$ROOT/build" \
  "${ADD_DATA[@]}" \
  --hidden-import PIL \
  --hidden-import PIL.Image \
  --hidden-import tkcalendar \
  --hidden-import openpyxl \
  --hidden-import reportlab \
  main.py

echo ""
echo "Build complete:"
ls -lh "$ROOT/dist/AmericanEdge_WaterDemand" 2>/dev/null || ls -lh "$ROOT/dist/"*
