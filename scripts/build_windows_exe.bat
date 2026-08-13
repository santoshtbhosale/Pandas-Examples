@echo off
REM Build American Edge Engineers Water Demand Report Generator (Windows EXE)
cd /d "%~dp0\.."

echo Rebuilding main.py from source modules...
python water_demand_app\build_main.py
if errorlevel 1 exit /b 1

echo Installing build dependencies...
pip install -r requirements.txt pyinstaller

echo Building Windows EXE...
pyinstaller --noconfirm --onefile --windowed ^
  --name "AmericanEdge_WaterDemand" ^
  --distpath "dist" ^
  --workpath "build" ^
  --specpath "build" ^
  main.py

if exist "dist\AmericanEdge_WaterDemand.exe" (
    echo.
    echo Build complete:
    echo   %CD%\dist\AmericanEdge_WaterDemand.exe
) else (
    echo Build failed.
    exit /b 1
)
