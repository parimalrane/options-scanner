import subprocess

try:
    out = subprocess.check_output(
        ["python", "analyze_flow.py", "--active", r"inputs\most-active-stock-options-08-05-2026.csv",
         "--decoi", r"inputs\stocks-decrease-change-in-open-interest-08-05-2026_OI.csv",
         "--incoi", r"inputs\stocks-increase-change-in-open-interest-08-05-2026_OI.csv",
         "--unusual", r"inputs\unusual-stock-options-activity-08-05-2026.csv",
         "--out", r"outputs\flagged-08-05-2026-TEST.csv"],
        stderr=subprocess.STDOUT
    )
    with open("stacktrace.txt", "w") as f:
        f.write(out.decode())
except subprocess.CalledProcessError as e:
    with open("stacktrace.txt", "w") as f:
        f.write(e.output.decode())
