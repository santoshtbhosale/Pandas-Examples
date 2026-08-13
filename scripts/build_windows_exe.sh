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
pyinstaller --noconfirm --onefile --windowed \
  --name "AmericanEdge_WaterDemand" \
  --distpath "$ROOT/dist" \
  --workpath "$ROOT/build" \
  --specpath "$ROOT/build" \
  main.py

echo ""
echo "Build complete:"
ls -lh "$ROOT/dist/AmericanEdge_WaterDemand" 2>/dev/null || ls -lh "$ROOT/dist/"*
