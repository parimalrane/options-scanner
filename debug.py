import csv

with open('inputs/options-flow-07-31-2026.csv', encoding='utf-8-sig') as f:
    rows = list(csv.DictReader(f))

groups = {}
for r in rows:
    if not r.get('Symbol') or r.get('Symbol').startswith('Downloaded'):
        continue
    groups.setdefault((r['Symbol'], r['Strike'], r['Exp Date']), []).append(r)

with open('debug.log', 'w') as f:
    f.write(f"Total groups: {len(groups)}\n")
    found = False
    for k, trades in groups.items():
        calls = [t for t in trades if t['Type'] == 'Call']
        puts = [t for t in trades if t['Type'] == 'Put']
        if calls and puts:
            f.write(f"Found combo group: {k}\n")
            for t in trades:
                f.write(f"  {t['Type']} | {t['Side']} | {t['*']} | {t['Premium']}\n")
            found = True
    if not found:
        f.write("No combos found.\n")
