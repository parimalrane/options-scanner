import os
import subprocess
out = subprocess.check_output(r"c:\options-scanner\run_scan.bat 08-05-2026", shell=True, cwd=r"c:\options-scanner")
with open(r"c:\options-scanner\bat_dump.txt", "w", encoding="utf-8") as f:
    f.write(out.decode())
