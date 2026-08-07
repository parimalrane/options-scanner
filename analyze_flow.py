"""
Daily Options Flow Scanner
---------------------------
Reads the 4 Barchart Premier exports and flags Signal A (Short Covering),
Signal B (Short Build-up), and Signal C (Confirmed Squeeze Setup).

Usage:
    python3 analyze_flow.py \
        --active most-active-stock-options-YYYY-MM-DD.csv \
        --flow options-flow-YYYY-MM-DD.csv \
        --decoi stocks-decrease-change-in-open-interest-YYYY-MM-DD.csv \
        --incoi stocks-increase-change-in-open-interest-YYYY-MM-DD.csv \
        --unusual unusual-stock-options-activity-YYYY-MM-DD.csv \
        --liquidity-min 10000 --moneyness-max 5
"""

import argparse
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

def build_watchlist(active_rows, liquidity_min):
    watchlist = {}
    for r in active_rows:
        sym = r.get('Symbol', '').strip()
        vol = to_num(r.get('Options Vol'))
        if sym and vol >= liquidity_min:
            watchlist[sym] = {
                'price': to_num(r.get('Latest')),
            }
    return watchlist

def build_voloi_map(unusual_rows):
    m = {}
    for r in unusual_rows:
        key = (r.get('Symbol'), r.get('Strike'), r.get('Type'), r.get('Exp Date'))
        m[key] = r.get('Vol/OI')
    return m

def update_snapshot(date_obj, all_rows_sets):
    if not date_obj:
        return
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
    if not current_date:
        return None
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
                    
    if not best_file:
        return None
        
    prices = {}
    with open(best_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            key = (r['Symbol'], r['Type'], r['Strike'], r['Exp Date'])
            prices[key] = float(r['MidPrice'])
    return prices

def get_mid_price(r):
    bid = to_num(r.get('Bid'))
    ask = to_num(r.get('Ask'))
    if bid == bid and ask == ask:
        return (bid + ask) / 2
    return float('nan')

def process_signal(rows, watchlist, prior_prices, voloi_map, moneyness_max, oi_chg_min, signal_type):
    groups = {}
    
    diag_1_total = len(rows)
    diag_2_watchlist = 0
    diag_3_oi_sign = 0
    diag_4_moneyness = 0
    diag_4b_oi_min = 0
    diag_5_both = 0
    
    stats_excluded_moneyness = 0
    stats_excluded_oi_min = 0
    stats_no_prior = 0
    
    diag_evaluable = 0
    diag_price_up = 0
    diag_price_down = 0
    diag_price_flat = 0
    
    max_oi_val = 0
    max_oi_sym = ''
    max_oi_type = ''
    max_oi_strike = ''
    max_oi_raw_row = {}
    
    for r in rows:
        oi_chg_raw = r.get('OI %Chg') if 'OI %Chg' in r else r.get('OI Chg')
        oi_chg = to_num(oi_chg_raw)
        
        if oi_chg == oi_chg and abs(oi_chg) > max_oi_val:
            max_oi_val = abs(oi_chg)
            max_oi_sym = r.get('Symbol', '')
            max_oi_type = r.get('Type', '')
            max_oi_strike = r.get('Strike', '')
            max_oi_raw_row = r
            
        sym = r.get('Symbol', '').strip()
        if sym not in watchlist:
            continue
        diag_2_watchlist += 1
        oi_valid = False
        if signal_type == 'A' and (oi_chg < 0): oi_valid = True
        if signal_type == 'B' and (oi_chg > 0): oi_valid = True
        
        moneyness = to_num(r.get('Moneyness'))
        mon_valid = False
        if signal_type == 'A':
            mon_valid = True
        elif moneyness == moneyness and abs(moneyness) <= moneyness_max:
            mon_valid = True
            
        oi_min_valid = False
        if abs(oi_chg) >= oi_chg_min:
            oi_min_valid = True
            
        if oi_valid:
            diag_3_oi_sign += 1
        if mon_valid:
            diag_4_moneyness += 1
        if oi_min_valid:
            diag_4b_oi_min += 1
        if oi_valid and mon_valid and oi_min_valid:
            diag_5_both += 1
            
        if not mon_valid:
            stats_excluded_moneyness += 1
            continue
            
        if not oi_min_valid:
            stats_excluded_oi_min += 1
            continue
            
        if not oi_valid:
            continue
            
        opt_type = r.get('Type')
        strike = r.get('Strike')
        exp = r.get('Exp Date')
        key = (sym, opt_type, strike, exp)
        
        mid_today = get_mid_price(r)
        if mid_today != mid_today:
            continue
            
        if prior_prices is None or key not in prior_prices:
            stats_no_prior += 1
            continue
            
        mid_prior = prior_prices[key]
        price_diff = mid_today - mid_prior
        price_up = price_diff > 0
        price_down = price_diff < 0
        
        diag_evaluable += 1
        if price_up: diag_price_up += 1
        elif price_down: diag_price_down += 1
        else: diag_price_flat += 1
        
        direction = None
        if signal_type == 'A':
            # Signal A: Short Covering
            if price_up:
                if opt_type == 'Call': direction = 'bullish'
                elif opt_type == 'Put': direction = 'bearish'
        elif signal_type == 'B':
            # Signal B: Short Build-Up
            if price_down:
                if opt_type == 'Put': direction = 'bullish'
                elif opt_type == 'Call': direction = 'bearish'
                
        if not direction:
            continue
            
        entry = {
            'symbol': sym,
            'type': opt_type,
            'strike': strike,
            'exp': exp,
            'direction': direction,
            'oi_chg': oi_chg,
            'price_diff': price_diff,
            'vol_oi': voloi_map.get(key, ''),
        }
        groups.setdefault((sym, direction), []).append(entry)
        
    diag_stats = {
        'diag_1_total': diag_1_total,
        'diag_2_watchlist': diag_2_watchlist,
        'diag_3_oi_sign': diag_3_oi_sign,
        'diag_4_moneyness': diag_4_moneyness,
        'diag_4b_oi_min': diag_4b_oi_min,
        'diag_5_both': diag_5_both,
        'excluded_moneyness': stats_excluded_moneyness,
        'excluded_oi_min': stats_excluded_oi_min,
        'no_prior': stats_no_prior,
        'evaluable': diag_evaluable,
        'price_up': diag_price_up,
        'price_down': diag_price_down,
        'price_flat': diag_price_flat,
        'max_oi_val': max_oi_val,
        'max_oi_sym': max_oi_sym,
        'max_oi_type': max_oi_type,
        'max_oi_strike': max_oi_strike,
        'max_oi_raw_row': max_oi_raw_row,
    }
        
    return groups, diag_stats

def consolidate_groups(groups, signal_name, watchlist):
    out = []
    for (sym, direction), entries in groups.items():
        entries.sort(key=lambda e: abs(e['oi_chg']), reverse=True)
        lead = entries[0]
        other_count = len(entries) - 1
        total_oi_chg = sum(e['oi_chg'] for e in entries)
        
        note = f"OI Chg {lead['oi_chg']:,.0f} at {lead['strike']} strike (Opt Price {lead['price_diff']:+.2f})"
        if other_count:
            note += f" (+{other_count} more strikes, total OI Chg {total_oi_chg:,.0f})"
            
        out.append({
            'signal': signal_name,
            'symbol': sym,
            'type': lead['type'],
            'strike': lead['strike'],
            'exp': lead['exp'],
            'direction': lead['direction'],
            'premium': None,
            'underlying_price': watchlist[sym]['price'] if sym in watchlist else float('nan'),
            'vol_oi': lead['vol_oi'],
            'note': note,
            '_oi_chg': lead['oi_chg'],
            '_price_diff': lead['price_diff'],
            '_other_count': other_count,
            '_total_oi_chg': total_oi_chg,
        })
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--active', required=True)
    ap.add_argument('--flow', required=False)
    ap.add_argument('--decoi', required=True)
    ap.add_argument('--incoi', required=False)
    ap.add_argument('--unusual', required=False)
    ap.add_argument('--liquidity-min', type=float, default=10000)
    ap.add_argument('--moneyness-max', type=float, default=5.0)
    ap.add_argument('--oi-chg-min', type=float, default=500.0)
    ap.add_argument('--premium-min', type=float, default=50000)
    ap.add_argument('--move-min', type=float, default=3)
    ap.add_argument('--out', default=None)
    ap.add_argument('--debug', action='store_true')
    args = ap.parse_args()

    date_obj = extract_file_date(args.active)

    active_rows = read_csv(args.active)
    decoi_rows = read_csv(args.decoi)
    incoi_rows = read_csv(args.incoi) if args.incoi else []
    unusual_rows = read_csv(args.unusual) if args.unusual else []

    watchlist = build_watchlist(active_rows, args.liquidity_min)
    voloi_map = build_voloi_map(unusual_rows)

    update_snapshot(date_obj, [decoi_rows, incoi_rows, unusual_rows])
    prior_prices = load_prior_snapshot(date_obj)

    stats = {
        'a_out': [], 'b_out': [], 'c_out': [],
        'missing_snapshot': prior_prices is None,
        'a_excluded_moneyness': 0, 'a_no_prior': 0,
        'b_excluded_moneyness': 0, 'b_no_prior': 0,
    }

    if prior_prices is not None:
        groups_a, stats_a = process_signal(decoi_rows, watchlist, prior_prices, voloi_map, args.moneyness_max, args.oi_chg_min, 'A')
        groups_b, stats_b = process_signal(incoi_rows, watchlist, prior_prices, voloi_map, args.moneyness_max, args.oi_chg_min, 'B')
        
        stats['a_stats'] = stats_a
        stats['b_stats'] = stats_b
        
        stats['a_out'] = consolidate_groups(groups_a, 'Signal A — Short Covering', watchlist)
        stats['b_out'] = consolidate_groups(groups_b, 'Signal B — Short Build-Up', watchlist)
        
        for (sym, direction) in groups_a.keys():
            if (sym, direction) in groups_b:
                stats['c_out'].append({
                    'signal': 'Signal C — Confirmed Squeeze Setup',
                    'symbol': sym,
                    'type': 'Combo',
                    'strike': 'Multi',
                    'exp': 'Multi',
                    'direction': direction,
                    'premium': None,
                    'underlying_price': watchlist[sym]['price'] if sym in watchlist else float('nan'),
                    'vol_oi': '',
                    'note': 'Both Short Covering and Short Build-Up criteria met.',
                    '_oi_chg': float('nan'),
                    '_price_diff': float('nan'),
                    '_other_count': 0,
                    '_total_oi_chg': 0,
                })

    results = stats['c_out'] + stats['a_out'] + stats['b_out']
    rank = {'Signal C — Confirmed Squeeze Setup': 1, 'Signal A — Short Covering': 2, 'Signal B — Short Build-Up': 3}
    results.sort(key=lambda x: (rank.get(x['signal'], 99), x['symbol']))

    symbol_directions = {}
    for r in results:
        symbol_directions.setdefault(r['symbol'], set()).add(r['direction'].lower())

    bullish_only = 0
    bearish_only = 0
    mixed_count = 0
    symbols_mixed = set()
    for sym, dirs in symbol_directions.items():
        if 'bullish' in dirs and 'bearish' in dirs:
            mixed_count += 1
            symbols_mixed.add(sym)
        elif 'bullish' in dirs:
            bullish_only += 1
        elif 'bearish' in dirs:
            bearish_only += 1

    date_str = date_obj.strftime('%Y-%m-%d') if date_obj else 'UNKNOWN'
    
    top_scan = (
        f"=== {date_str} SCAN ===\n"
        f"Watchlist: {len(watchlist)} | Signals: {len(stats['a_out'])}A / {len(stats['b_out'])}B / {len(stats['c_out'])}C\n"
        f"Bias: {bullish_only} bullish-only | {bearish_only} bearish-only | {mixed_count} mixed"
    )
    print(top_scan)

    if args.out:
        out_dir = os.path.dirname(args.out)
        if out_dir: os.makedirs(out_dir, exist_ok=True)
    txt_out = args.out.replace('.csv', '.txt') if args.out else None
    f_txt = open(txt_out, 'w', encoding='utf-8') if txt_out else None

    if f_txt:
        f_txt.write(top_scan + "\n\n")

    diag_msgs = []
    if stats['missing_snapshot']:
        diag_msgs.append("NOTE: No prior price snapshot available. Required to determine option price direction.")
        diag_msgs.append("Generated snapshot for today. Run tomorrow to see signals.")
    else:
        a_s = stats['a_stats']
        b_s = stats['b_stats']
        diag_msgs.append(f"--- DIAGNOSTICS: Signal A ({a_s['diag_1_total']} rows) ---")
        diag_msgs.append(f"  1. Total rows       : {a_s['diag_1_total']}")
        diag_msgs.append(f"  2. Watchlist match  : {a_s['diag_2_watchlist']}")
        diag_msgs.append(f"  3. OI Sign (< 0)    : {a_s['diag_3_oi_sign']}")
        diag_msgs.append(f"  4. OI Magnitude     : {a_s['diag_4b_oi_min']}")
        diag_msgs.append(f"  5. Matched          : {a_s['diag_5_both']}")
        diag_msgs.append(f"--- DIAGNOSTICS: Signal B ({b_s['diag_1_total']} rows) ---")
        diag_msgs.append(f"  1. Total rows       : {b_s['diag_1_total']}")
        diag_msgs.append(f"  2. Watchlist match  : {b_s['diag_2_watchlist']}")
        diag_msgs.append(f"  3. OI Sign (> 0)    : {b_s['diag_3_oi_sign']}")
        diag_msgs.append(f"  4. Moneyness filter : {b_s['diag_4_moneyness']}")
        diag_msgs.append(f"  5. OI Magnitude     : {b_s['diag_4b_oi_min']}")
        diag_msgs.append(f"  6. Matched BOTH     : {b_s['diag_5_both']}")
        diag_msgs.append("---------------------------------")
        diag_msgs.append(f"Total Strikes excluded by Moneyness filter (>{args.moneyness_max}%): {a_s['excluded_moneyness'] + b_s['excluded_moneyness']}")
        diag_msgs.append(f"Total Strikes excluded by Minimum OI Magnitude filter (<{args.oi_chg_min}): {a_s['excluded_oi_min'] + b_s['excluded_oi_min']}")
        diag_msgs.append(f"Largest |OI Chg| seen in today's decoi file: {int(a_s['max_oi_val'])} ({a_s['max_oi_sym']} {a_s['max_oi_type']} {a_s['max_oi_strike']}), vs current oi-chg-min threshold of {args.oi_chg_min}")
        diag_msgs.append(f"   -> RAW ROW: {a_s['max_oi_raw_row']}")
        diag_msgs.append(f"Total Strikes skipped lacking prior-snapshot price data: {a_s['no_prior'] + b_s['no_prior']}")
        diag_msgs.append(f"Signal A evaluable strikes: {a_s['evaluable']} (price up: {a_s['price_up']}, price down: {a_s['price_down']}, flat: {a_s['price_flat']})")
        diag_msgs.append(f"Signal B evaluable strikes: {b_s['evaluable']} (price down: {b_s['price_down']}, price up: {b_s['price_up']}, flat: {b_s['price_flat']})")
        diag_msgs.append(f"Signal C (Confirmed Squeeze Setup): {len(stats['c_out'])}")
        diag_msgs.append(f"Signal A (Short Covering): {len(stats['a_out'])}")
        diag_msgs.append(f"Signal B (Short Build-Up): {len(stats['b_out'])}")

    if diag_msgs:
        diag_path = f"outputs/diagnostics-{date_str}.txt"
        os.makedirs("outputs", exist_ok=True)
        with open(diag_path, "a", encoding="utf-8") as df:
            df.write(f"\n=== ANALYZE FLOW DIAGNOSTICS ===\n")
            for m in diag_msgs:
                if getattr(args, 'debug', False):
                    print(m)
                df.write(m + "\n")

    results_by_symbol = {}
    for r in results:
        results_by_symbol.setdefault(r['symbol'], []).append(r)

    mixed_syms = sorted(list(symbols_mixed))
    single_syms = sorted([s for s in results_by_symbol if s not in symbols_mixed])

    if mixed_syms:
        quick_scan_title = "QUICK-SCAN LIST (Mixed Signals):"
        print(quick_scan_title)
        if f_txt: f_txt.write(quick_scan_title + "\n")
        
        for sym in mixed_syms:
            sym_signals = results_by_symbol[sym]
            sym_signals.sort(key=lambda x: (rank.get(x['signal'], 99), x.get('exp', '')))
            codes = []
            for r in sym_signals:
                code = 'C' if 'Signal C' in r['signal'] else ('A' if 'Signal A' in r['signal'] else 'B')
                arr = '▲' if r['direction'] == 'bullish' else '▼'
                codes.append(f"{code}{arr}")
            q_line = f"  {sym}:  {' '.join(codes)}"
            print(q_line)
            if f_txt: f_txt.write(q_line + "\n")
            
        print("-" * 140)
        if f_txt: f_txt.write("-" * 140 + "\n")

    if mixed_syms:
        lbl = "--- MIXED ---"
        print(lbl)
        if f_txt: f_txt.write(lbl + "\n")
        
        for sym in mixed_syms:
            sym_signals = results_by_symbol[sym]
            sym_signals.sort(key=lambda x: (rank.get(x['signal'], 99), x.get('exp', '')))
            
            sym_header = f"{sym}"
            print(sym_header)
            if f_txt: f_txt.write(sym_header + "\n")
                
            table_header = f"  {'DIR':4} | {'SIG':3} | {'TYPE':5} | {'STRIKE':>8} | {'EXP':10} | {'OI CHG':>10} | {'PRICE Δ':>8}"
            print(table_header)
            if f_txt: f_txt.write(table_header + "\n")
                
            for r in sym_signals:
                arr = '▲' if r['direction'] == 'bullish' else '▼'
                code = 'C' if 'Signal C' in r['signal'] else ('A' if 'Signal A' in r['signal'] else 'B')
                
                strike = str(r['strike'])
                exp = str(r['exp'])
                
                oi_chg_str = f"{r.get('_oi_chg', float('nan')):,.0f}" if r.get('_oi_chg') == r.get('_oi_chg') else ""
                price_diff_str = f"{r.get('_price_diff', float('nan')):+.2f}" if r.get('_price_diff') == r.get('_price_diff') else ""
                
                line = f"  {arr:4} | {code:3} | {r['type']:5} | {strike:>8} | {exp:10} | {oi_chg_str:>10} | {price_diff_str:>8}"
                if r.get('_other_count', 0) > 0:
                    line += f"  (+{r['_other_count']}, Σ{r['_total_oi_chg']:,.0f})"
                if r.get('vol_oi'):
                    line += f"  (Vol/OI {r['vol_oi']})"
                    
                print(line)
                if f_txt: f_txt.write(line + "\n")
            print()
            if f_txt: f_txt.write("\n")

    if single_syms:
        # count total single signals
        total_single_signals = sum(len(results_by_symbol[s]) for s in single_syms)
        msg = f"{total_single_signals} single-direction signals — full list in {args.out}"
        print(msg)
        if f_txt:
            f_txt.write(msg + "\n")

    if f_txt:
        f_txt.close()

    if args.out:
        fieldnames = ['signal', 'symbol', 'type', 'strike', 'exp', 'direction',
                      'premium', 'underlying_price', 'vol_oi', 'note']
        with open(args.out, 'w', newline='', encoding='utf-8') as dest:
            w = csv.DictWriter(dest, fieldnames=fieldnames, extrasaction='ignore')
            w.writeheader()
            for r in results:
                w.writerow(r)
        print(f"\nWrote {len(results)} candidates to {args.out}")

    return results

if __name__ == '__main__':
    main()
