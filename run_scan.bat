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

set ER=inputs\earnings-in-the-next-trading-day-%TARGET_DATE%.csv
set IVR_HIGH=inputs\implied-volatility-iv-rank-and-iv-percentile-high-%TARGET_DATE%.csv
set IV_RV_HIGH=inputs\stocks-high-implied-volatility-vs-realized-volatility-us-%TARGET_DATE%.csv
set IV_RV_HIGH_ETF=inputs\etfs-high-implied-volatility-vs-realized-volatility-us-%TARGET_DATE%.csv

set ER_ARG=
if exist "%ER%" set ER_ARG=--earnings "%ER%"

set IVR_HIGH_ARG=
if exist "%IVR_HIGH%" set IVR_HIGH_ARG=--ivr-high "%IVR_HIGH%"

set IV_RV_HIGH_ARG=
if exist "%IV_RV_HIGH%" set IV_RV_HIGH_ARG=--ivrv-high "%IV_RV_HIGH%"
if exist "%IV_RV_HIGH_ETF%" set IV_RV_HIGH_ARG=%IV_RV_HIGH_ARG% "%IV_RV_HIGH_ETF%"

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
if not exist "%INCOI%" (
    echo MISSING: %INCOI%
    set MISSING=1
)
if not exist "%UNUSUAL%" (
    echo MISSING: %UNUSUAL%
    set MISSING=1
)

if defined MISSING (
    echo.
    echo ---------------------------------------------------
    echo  ERROR: CORE FILES MISSING!
    echo  The pipeline absolutely requires the following 4 files:
    echo  - most-active-stock-options
    echo  - stocks-decrease-change-in-open-interest
    echo  - stocks-increase-change-in-open-interest
    echo  - unusual-stock-options-activity
    echo  Please download them to the inputs\ directory.
    echo ---------------------------------------------------
    exit /b 1
)

if not exist "%FLOW%" (
    set FLOW_ARG=
) else (
    set FLOW_ARG=--flow "%FLOW%"
)

set INCOI_ARG=--incoi "%INCOI%"
if exist "%INCOI_ETF%" set INCOI_ARG=--incoi "%INCOI%" "%INCOI_ETF%"

set UNUSUAL_ARG=--unusual "%UNUSUAL%"
if exist "%UNUSUAL_ETF%" set UNUSUAL_ARG=--unusual "%UNUSUAL%" "%UNUSUAL_ETF%"


python analyze_flow.py --active %ACTIVE_ARGS% %FLOW_ARG% --decoi %DECOI_ARGS% %INCOI_ARG% %UNUSUAL_ARG% %ER_ARG% %IVR_HIGH_ARG% %IV_RV_HIGH_ARG% --out "%OUT%" %DEBUG_ARG%

if errorlevel 1 (
    echo.
    echo analyze_flow.py failed - stopping before touching the log.
    exit /b 1
)

