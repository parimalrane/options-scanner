import csv
import os
import glob
import re
from datetime import datetime

def read_csv(path):
    with open(path, newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

def to_num(v):
    if v is None:
        return float('nan')
    s = str(v).replace(',', '').replace('%', '').replace('$', '').replace('+', '').strip()
    try:
        return float(s)
    except ValueError:
        return float('nan')

def extract_file_date(filepath):
    base = os.path.basename(filepath)
    m = re.search(r'(\d{2}-\d{2}-\d{4})', base)
    if m:
        try:
            return datetime.strptime(m.group(1), '%m-%d-%Y')
        except ValueError:
            pass
    return None

def update_snapshot(date_obj, all_rows_sets):
    if not date_obj: return
    date_str = date_obj.strftime('%Y-%m-%d')
    os.makedirs('snapshots', exist_ok=True)
    snapshot_path = f'snapshots/prices-{date_str}.csv'
    
    prices = {}
    for rows in all_rows_sets:
        for r in rows:
            sym = r.get('Symbol')
            if not sym: continue
            typ = r.get('Type')
            strike = r.get('Strike')
            exp = r.get('Exp Date')
            bid = to_num(r.get('Bid'))
            ask = to_num(r.get('Ask'))
            
            if bid == bid and ask == ask: # not nan
                mid = (bid + ask) / 2
                key = (sym, typ, strike, exp)
                if key not in prices:
                    prices[key] = mid

    with open(snapshot_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['Symbol', 'Type', 'Strike', 'Exp Date', 'MidPrice'])
        for (sym, typ, strike, exp), mid in prices.items():
            w.writerow([sym, typ, strike, exp, f"{mid:.4f}"])

def load_prior_snapshot(current_date):
    if not current_date: return None
    os.makedirs('snapshots', exist_ok=True)
    files = glob.glob('snapshots/prices-*.csv')
    best_date = None
    best_file = None
    
    for f in files:
        base = os.path.basename(f)
        m = re.search(r'prices-(\d{4}-\d{2}-\d{2})\.csv', base)
        if m:
            d = datetime.strptime(m.group(1), '%Y-%m-%d')
            if d < current_date:
                if not best_date or d > best_date:
                    best_date = d
                    best_file = f
                    
    if not best_file: return None
        
    prices = {}
    with open(best_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            key = (r['Symbol'], r['Type'], r['Strike'], r['Exp Date'])
            prices[key] = float(r['MidPrice'])
    return prices
