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

set DATE=%1

if "%DATE%"=="" (
    echo ERROR: You must pass the market closing date ^(matching your renamed files^).
    echo Usage: run_scan.bat MM-DD-YYYY [debug]
    echo Example: run_scan.bat 07-31-2026
    exit /b 1
)

set DEBUG_ARG=
if /I "%2"=="debug" (
    set DEBUG_ARG=--debug
)

set MISSING=
set ACTIVE=inputs\most-active-stock-options-%DATE%.csv
set FLOW=inputs\options-flow-%DATE%.csv
set DECOI=inputs\stocks-decrease-change-in-open-interest-%DATE%.csv
set INCOI=inputs\stocks-increase-change-in-open-interest-%DATE%.csv
set UNUSUAL=inputs\unusual-stock-options-activity-%DATE%.csv
set OUT=outputs\flagged-%DATE%.csv





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
    echo One or more required files are missing. Check the filenames match %DATE% exactly, then try again.
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
)

if not exist "%UNUSUAL%" (
    echo NOTE: %UNUSUAL% not found - continuing without it, Vol/OI cross-check will be blank.
    set UNUSUAL_ARG=
) else (
    set UNUSUAL_ARG=--unusual "%UNUSUAL%"
)


python analyze_flow.py --active "%ACTIVE%" %FLOW_ARG% --decoi "%DECOI%" %INCOI_ARG% %UNUSUAL_ARG% --out "%OUT%" %DEBUG_ARG%

if errorlevel 1 (
    echo.
    echo analyze_flow.py failed - stopping before touching the log.
    exit /b 1
)

set MM=%DATE:~0,2%
set DD=%DATE:~3,2%
set YYYY=%DATE:~6,4%
set ISODATE=%YYYY%-%MM%-%DD%


python manage_log.py --flagged "%OUT%" --date %ISODATE% --log options-log.csv %DEBUG_ARG%


