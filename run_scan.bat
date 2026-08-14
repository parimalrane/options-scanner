@echo off
REM ============================================================
REM  run_scan.bat
REM  Usage:  run_scan.bat MM-DD-YYYY
REM  Example: run_scan.bat 08-02-2026
REM
REM  Expects these 5 files already downloaded into inputs\ with
REM  the same date suffix:
REM    most-active-stock-options-MM-DD-YYYY.csv
REM    options-flow-MM-DD-YYYY.csv
REM    stocks-decrease-change-in-open-interest-MM-DD-YYYY.csv
REM    stocks-increase-change-in-open-interest-MM-DD-YYYY.csv
REM    unusual-stock-options-activity-MM-DD-YYYY.csv
REM ============================================================

set TARGET_DATE=%1

if "%TARGET_DATE%"=="" (
    for /f "usebackq tokens=*" %%i in (`powershell -NoProfile -Command "Get-Date -Format 'MM-dd-yyyy'"`) do set TARGET_DATE=%%i
    echo No date provided. Defaulting to today's date: %TARGET_DATE%
) else (
    echo Running scan for date: %TARGET_DATE%
)

set DEBUG_ARG=
if /I "%2"=="debug" (
    set DEBUG_ARG=--debug
)

set MISSING=
set ACTIVE=inputs\most-active-stock-options-%TARGET_DATE%.csv
set FLOW=inputs\options-flow-%TARGET_DATE%.csv
set DECOI=inputs\stocks-decrease-change-in-open-interest-%TARGET_DATE%.csv
set INCOI=inputs\stocks-increase-change-in-open-interest-%TARGET_DATE%.csv
set UNUSUAL=inputs\unusual-stock-options-activity-%TARGET_DATE%.csv
set OUT=outputs\flagged-%TARGET_DATE%.csv

set ACTIVE_ETF=inputs\most-active-etf-options-%TARGET_DATE%.csv
set DECOI_ETF=inputs\etfs-decrease-change-in-open-interest-%TARGET_DATE%.csv
set INCOI_ETF=inputs\etfs-increase-change-in-open-interest-%TARGET_DATE%.csv
set UNUSUAL_ETF=inputs\unusual-etf-options-activity-%TARGET_DATE%.csv

set ACTIVE_ARGS="%ACTIVE%"
if exist "%ACTIVE_ETF%" set ACTIVE_ARGS="%ACTIVE%" "%ACTIVE_ETF%"

set DECOI_ARGS="%DECOI%"
if exist "%DECOI_ETF%" set DECOI_ARGS="%DECOI%" "%DECOI_ETF%"

if not exist "%ACTIVE%" (
    echo MISSING: %ACTIVE%
    set MISSING=1
)
if not exist "%DECOI%" (
    echo MISSING: %DECOI%
    set MISSING=1
)

if defined MISSING (
    echo.
    echo One or more required files are missing. Check the filenames match %TARGET_DATE% exactly, then try again.
    exit /b 1
)

if not exist "%FLOW%" (
    set FLOW_ARG=
) else (
    set FLOW_ARG=--flow "%FLOW%"
)

if not exist "%INCOI%" (
    echo NOTE: %INCOI% not found - skipping Signal B ^(Short Build-Up^).
    set INCOI_ARG=
) else (
    set INCOI_ARG=--incoi "%INCOI%"
    if exist "%INCOI_ETF%" set INCOI_ARG=--incoi "%INCOI%" "%INCOI_ETF%"
)

if not exist "%UNUSUAL%" (
    echo NOTE: %UNUSUAL% not found - continuing without it, Vol/OI cross-check will be blank.
    set UNUSUAL_ARG=
) else (
    set UNUSUAL_ARG=--unusual "%UNUSUAL%"
    if exist "%UNUSUAL_ETF%" set UNUSUAL_ARG=--unusual "%UNUSUAL%" "%UNUSUAL_ETF%"
)


python analyze_flow.py --active %ACTIVE_ARGS% %FLOW_ARG% --decoi %DECOI_ARGS% %INCOI_ARG% %UNUSUAL_ARG% --out "%OUT%" %DEBUG_ARG%

if errorlevel 1 (
    echo.
    echo analyze_flow.py failed - stopping before touching the log.
    exit /b 1
)

