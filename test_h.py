import csv
with open('inputs/stocks-decrease-change-in-open-interest-08-04-2026.csv', encoding='utf-8-sig') as f:
    r = csv.DictReader(f)
    with open('headers_out.txt', 'w', encoding='utf-8') as out:
        out.write(str(r.fieldnames) + '\n')
        out.write(str(list(r)[0]) + '\n')
