@echo off
echo ============================================================
echo    EcoTrack — Carbon Footprint Web Application
echo ============================================================
echo.

REM Use the Python found in the codex runtime or adjust to your Python path
SET PYTHON="C:\Users\SAHANA JADHAV\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

echo [1] Setting up MySQL database...
echo     Please ensure MySQL is running and credentials are correct in config.py
echo     Default: host=localhost, user=root, password=root, db=carbon_db
echo.
echo     To create the database, run schema.sql in MySQL Workbench or:
echo     mysql -u root -p ^< schema.sql
echo.

echo [2] Starting Flask application...
set FLASK_APP=app.py
set FLASK_ENV=development
%PYTHON% -m flask run --host=0.0.0.0 --port=5000 --debug

pause
