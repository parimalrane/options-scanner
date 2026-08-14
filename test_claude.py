import subprocess
orig_path = 'inputs/stocks-decrease-change-in-open-interest-08-13-2026.csv'
with open(orig_path, 'r', encoding='utf-8') as f: orig_content = f.read()
def run_test(label):
    subprocess.run(['run_scan.bat', '08-13-2026'], shell=True, capture_output=True, text=True)
    with open('outputs/flagged-08-13-2026.txt', 'r', encoding='utf-8') as f: return f.read()
try:
    with open(orig_path, 'w', encoding='utf-8') as f: f.write(orig_content)
    baseline = run_test('Baseline')
    mod_1 = orig_content.replace('-6,892', '-99999')
    with open(orig_path, 'w', encoding='utf-8') as f: f.write(mod_1)
    smci_test = run_test('SMCI -99999')
    nvda_row = '\nNVDA,225.3,2026-08-14,1,Call,999.00,+2.35%,5.6,5.75,17888,15785,"-450",1.13,42.43%,0.861469,2026-08-13\n'
    nvda_row_2 = '\nNVDA,225.3,2026-08-14,1,Call,999.00,+2.35%,5.6,5.75,17888,15785,"-550",1.13,42.43%,0.861469,2026-08-13\n'
    with open(orig_path, 'w', encoding='utf-8') as f: f.write(orig_content + nvda_row)
    nvda_450_test = run_test('NVDA 450')
    with open(orig_path, 'w', encoding='utf-8') as f: f.write(orig_content + nvda_row_2)
    nvda_550_test = run_test('NVDA 550')
finally:
    with open(orig_path, 'w', encoding='utf-8') as f: f.write(orig_content)
    run_test('Restore')
smci_base_lines = [l for l in baseline.splitlines() if 'SMCI ' in l]
smci_mod_lines = [l for l in smci_test.splitlines() if 'SMCI ' in l]
nvda_450_lines = [l for l in nvda_450_test.splitlines() if '999.00 ' in l]
nvda_550_lines = [l for l in nvda_550_test.splitlines() if '999.00 ' in l]
summary = "# CACHING DIFF\n"
summary += "Baseline SMCI outputs:\n" + '\n'.join(smci_base_lines) + "\n\n"
summary += "Modified SMCI outputs (-99,999):\n" + '\n'.join(smci_mod_lines) + "\n\n"
summary += "# OI FILTER DIFF\n"
summary += "Output with NVDA OI Chg = -450 (Sub-threshold):\n" + '\n'.join(nvda_450_lines) + " (Blank line = successfully excluded!)\n\n"
summary += "Output with NVDA OI Chg = -550 (Above threshold):\n" + '\n'.join(nvda_550_lines) + "\n"
with open('test_results.txt', 'w', encoding='utf-8') as f: f.write(summary)
