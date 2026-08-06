import csv

def to_num(s):
    try:
        return float(str(s).replace(',', '').replace('+', '').replace('%', '').strip())
    except:
        return float('nan')

with open('inputs/stocks-decrease-change-in-open-interest-08-05-2026.csv', encoding='utf-8-sig') as f:
    r = list(csv.DictReader(f))
    
    max_val = 0
    max_row = None
    
    for row in r:
        val = to_num(row.get('OI %Chg') if 'OI %Chg' in row else row.get('OI Chg'))
        if val == val and abs(val) > max_val:
            max_val = abs(val)
            max_row = row
            
    with open('max_out.txt', 'w', encoding='utf-8') as out:
        out.write("MAX VAL SCANNED: " + str(max_val) + "\n")
        out.write("RAW ROW: " + str(max_row) + "\n")
