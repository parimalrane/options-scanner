import csv

with open('inputs/stocks-decrease-change-in-open-interest-08-03-2026.csv', encoding='utf-8-sig') as f:
    dec_r = csv.DictReader(f)
    dec_fields = dec_r.fieldnames
    dec_first5 = list(dec_r)[:5]

with open('inputs/stocks-increase-change-in-open-interest-08-03-2026.csv', encoding='utf-8-sig') as f:
    inc_r = csv.DictReader(f)
    inc_fields = inc_r.fieldnames
    inc_first5 = list(inc_r)[:5]

with open('debug_headers.txt', 'w') as f:
    f.write(f"DECOI Headers: {dec_fields}\n")
    f.write("DECOI first 5:\n")
    for r in dec_first5:
        f.write(f"  raw OI Chg: {r.get('OI Chg', r.get('Open Int Chg', str(r)))}\n")

    f.write(f"\nINCOI Headers: {inc_fields}\n")
    f.write("INCOI first 5:\n")
    for r in inc_first5:
        f.write(f"  raw OI Chg: {r.get('OI Chg', r.get('Open Int Chg', str(r)))}\n")
