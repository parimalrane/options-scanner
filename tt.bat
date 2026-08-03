@echo on
set DATE=07-31-2026
set ACTIVE=inputs\most-active-stock-options-%DATE%.csv
set FLOW=inputs\options-flow-%DATE%.csv
set DECOI=inputs\stocks-decrease-change-in-open-interest-%DATE%.csv
set INCOI=inputs\stocks-increase-change-in-open-interest-%DATE%.csv
set UNUSUAL=inputs\unusual-stock-options-activity-%DATE%.csv
set OUT=outputs\flagged-%DATE%.csv

if not exist "%INCOI%" (
    echo NOTE: %INCOI% not found - skipping Signal 4 ^(Trend Conviction^).
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

python analyze_flow.py --active "%ACTIVE%" --flow "%FLOW%" --decoi "%DECOI%" %INCOI_ARG% %UNUSUAL_ARG% --out "%OUT%"
