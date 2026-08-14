@echo off
REM Build American Edge Engineers Water Demand Report Generator (Windows EXE)
cd /d "%~dp0\.."

echo Rebuilding main.py from source modules...
python water_demand_app\build_main.py
if errorlevel 1 exit /b 1

echo Installing build dependencies...
pip install -r requirements.txt pyinstaller

set ADD_DATA=
if exist "logo.png" set ADD_DATA=%ADD_DATA% --add-data "logo.png;."
if exist "water_demand_app\assets\logo.png" set ADD_DATA=%ADD_DATA% --add-data "water_demand_app\assets\logo.png;assets"
if exist "templates\WaterDemand_Template.xlsx" set ADD_DATA=%ADD_DATA% --add-data "templates\WaterDemand_Template.xlsx;templates"

echo Building Windows EXE...
pyinstaller --noconfirm --onefile --windowed ^
  --name "AmericanEdge_WaterDemand" ^
  --distpath "dist" ^
  --workpath "build" ^
  --specpath "build" ^
  --hidden-import PIL ^
  --hidden-import PIL.Image ^
  --hidden-import tkcalendar ^
  --hidden-import openpyxl ^
  --hidden-import reportlab ^
  %ADD_DATA% ^
  main.py

if exist "dist\AmericanEdge_WaterDemand.exe" (
    echo.
    echo Build complete:
    echo   %CD%\dist\AmericanEdge_WaterDemand.exe
) else (
    echo Build failed.
    exit /b 1
)
