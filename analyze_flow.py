"""
Daily Options Flow Scanner
---------------------------
Reads the 4 Barchart Premier exports and flags Signal 1 (panic covering)
and Signal 2 (aggressive buy-to-open) candidates per the trader's rubric.

Usage:
    python3 analyze_flow.py \
        --active most-active-stock-options-YYYY-MM-DD.csv \
        --flow options-flow-YYYY-MM-DD.csv \
        --decoi stocks-decrease-change-in-open-interest-YYYY-MM-DD.csv \
        --incoi stocks-increase-change-in-open-interest-YYYY-MM-DD.csv \
        --unusual unusual-stock-options-activity-YYYY-MM-DD.csv \
        --liquidity-min 10000 --premium-min 50000 --move-min 3
"""

import argparse
import csv
import os
import sys
from datetime import datetime, timezone


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


def build_watchlist(active_rows, liquidity_min):
    watchlist = {}
    for r in active_rows:
        sym = r.get('Symbol', '').strip()
        vol = to_num(r.get('Options Vol'))
        pct = to_num(r.get('%Change'))
        if sym and vol >= liquidity_min:
            watchlist[sym] = {
                'vol': vol,
                'pct': 0.0 if pct != pct else pct,  # NaN check
                'price': to_num(r.get('Latest')),
            }
    return watchlist


def build_voloi_map(unusual_rows):
    m = {}
    for r in unusual_rows:
        key = (r.get('Symbol'), r.get('Strike'), r.get('Type'), r.get('Exp Date'))
        m[key] = r.get('Vol/OI')
    return m


def dedup_flow_rows(flow_rows):
    """
    Barchart's Options Flow export re-lists the same trade across successive
    ~5-minute snapshots as it gets reclassified (Side/label can change between
    appearances). Collapse to one row per (Symbol, Type, Strike, Exp, Premium),
    keeping the most decisive snapshot: prefer a real open/close label over
    N/A, then prefer a real Side (ask/bid) over 'mid'.
    """
    def rank(r):
        label_rank = 0 if (r.get('*') or 'N/A') != 'N/A' else 1
        side = (r.get('Side') or '').lower()
        side_rank = 0 if side in ('ask', 'bid') else 1
        return (label_rank, side_rank)

    best = {}
    for r in flow_rows:
        key = (r.get('Symbol'), r.get('Type'), r.get('Strike'),
               r.get('Exp Date'), r.get('Premium'))
        if key not in best or rank(r) < rank(best[key]):
            best[key] = r
    return list(best.values())


def scan_signal2_and_3(flow_rows, watchlist, voloi_map, premium_min):
    flow_rows = dedup_flow_rows(flow_rows)
    
    # Group by (Symbol, Exp Date)
    groups = {}
    for r in flow_rows:
        sym = r.get('Symbol', '').strip()
        if sym not in watchlist:
            continue
        exp = r.get('Exp Date')
        groups.setdefault((sym, exp), []).append(r)
        
    out = []
    for (sym, exp), trades in groups.items():
        long_calls = []
        short_puts = []
        long_puts = []
        short_calls = []
        
        for r in trades:
            opt_type = r.get('Type')
            side = (r.get('Side') or '').lower()
            open_label = r.get('*') or ''
            premium = to_num(r.get('Premium'))
            
            if not (premium >= premium_min):
                continue
                
            if opt_type == 'Call':
                if side == 'ask' and open_label in ('BuyToOpen', 'ToOpen'):
                    long_calls.append(r)
                elif side == 'bid' and open_label in ('SellToOpen', 'ToOpen'):
                    short_calls.append(r)
            elif opt_type == 'Put':
                if side == 'ask' and open_label in ('BuyToOpen', 'ToOpen'):
                    long_puts.append(r)
                elif side == 'bid' and open_label in ('SellToOpen', 'ToOpen'):
                    short_puts.append(r)
                    
        # Check Signal 3: Bullish Risk Reversal (Long Call + Short Put)
        if long_calls and short_puts:
            lc = max(long_calls, key=lambda x: to_num(x.get('Premium')))
            sp = max(short_puts, key=lambda x: to_num(x.get('Premium')))
            long_calls.remove(lc)
            short_puts.remove(sp)
            total_prem = to_num(lc.get('Premium')) + to_num(sp.get('Premium'))
            key = (sym, lc.get('Strike'), 'Call', exp)
            out.append({
                'signal': 'Signal 3 — Bullish Risk Reversal',
                'symbol': sym,
                'type': 'C+P',
                'strike': f"{lc.get('Strike')}/{sp.get('Strike')}",
                'exp': exp,
                'direction': 'bullish',
                'premium': total_prem,
                'underlying_price': watchlist[sym]['price'],
                'vol_oi': voloi_map.get(key, ''),
                'note': f"Risk Rev (Bot C {lc.get('Strike')}, Sold P {sp.get('Strike')}) Total Prem: ${total_prem:,.0f}",
            })
            
        # Check Signal 3: Bearish Risk Reversal (Long Put + Short Call)
        if long_puts and short_calls:
            lp = max(long_puts, key=lambda x: to_num(x.get('Premium')))
            sc = max(short_calls, key=lambda x: to_num(x.get('Premium')))
            long_puts.remove(lp)
            short_calls.remove(sc)
            total_prem = to_num(lp.get('Premium')) + to_num(sc.get('Premium'))
            key = (sym, lp.get('Strike'), 'Put', exp) 
            out.append({
                'signal': 'Signal 3 — Bearish Risk Reversal',
                'symbol': sym,
                'type': 'P+C',
                'strike': f"{lp.get('Strike')}/{sc.get('Strike')}",
                'exp': exp,
                'direction': 'bearish',
                'premium': total_prem,
                'underlying_price': watchlist[sym]['price'],
                'vol_oi': voloi_map.get(key, ''),
                'note': f"Risk Rev (Bot P {lp.get('Strike')}, Sold C {sc.get('Strike')}) Total Prem: ${total_prem:,.0f}",
            })

        # Signal 2: Naked Whale Sweeps (Remaining Long Calls and Long Puts)
        for lc in long_calls:
            prem = to_num(lc.get('Premium'))
            key = (sym, lc.get('Strike'), 'Call', exp)
            out.append({
                'signal': 'Signal 2 — Naked Whale Sweep',
                'symbol': sym,
                'type': 'Call',
                'strike': lc.get('Strike'),
                'exp': exp,
                'direction': 'bullish',
                'premium': prem,
                'underlying_price': watchlist[sym]['price'],
                'vol_oi': voloi_map.get(key, ''),
                'note': f"Aggressive Sweep, BuyToOpen at ask, Premium ${prem:,.0f}",
            })
            
        for lp in long_puts:
            prem = to_num(lp.get('Premium'))
            key = (sym, lp.get('Strike'), 'Put', exp)
            out.append({
                'signal': 'Signal 2 — Naked Whale Sweep',
                'symbol': sym,
                'type': 'Put',
                'strike': lp.get('Strike'),
                'exp': exp,
                'direction': 'bearish',
                'premium': prem,
                'underlying_price': watchlist[sym]['price'],
                'vol_oi': voloi_map.get(key, ''),
                'note': f"Aggressive Sweep, BuyToOpen at ask, Premium ${prem:,.0f}",
            })
            
    return out


def scan_signal1(decoi_rows, watchlist, voloi_map, move_min):
    # First pass: collect every strike that qualifies, grouped by (symbol, direction).
    groups = {}
    for r in decoi_rows:
        sym = r.get('Symbol', '').strip()
        if sym not in watchlist:
            continue
        oi_chg = to_num(r.get('OI Chg'))
        if not (oi_chg < 0):
            continue
        pct = watchlist[sym]['pct']
        opt_type = r.get('Type')
        direction = None
        if opt_type == 'Call' and pct >= move_min:
            direction = 'bullish'   # call sellers covering into a rally
        elif opt_type == 'Put' and pct <= -move_min:
            direction = 'bearish'  # put sellers covering into a selloff
        if not direction:
            continue
        key = (sym, r.get('Strike'), opt_type, r.get('Exp Date'))
        entry = {
            'symbol': sym,
            'type': opt_type,
            'strike': r.get('Strike'),
            'exp': r.get('Exp Date'),
            'direction': direction,
            'oi_chg': oi_chg,
            'pct': pct,
            'vol_oi': voloi_map.get(key, ''),
        }
        groups.setdefault((sym, direction), []).append(entry)

    # Second pass: one headline row per (symbol, direction) — the largest single
    # OI-drop strike — with a note on how many other strikes also qualified,
    # so a broad market-wide move doesn't flood the list with near-duplicates.
    out = []
    for (sym, direction), entries in groups.items():
        entries.sort(key=lambda e: e['oi_chg'])  # most negative first
        lead = entries[0]
        other_count = len(entries) - 1
        total_oi_chg = sum(e['oi_chg'] for e in entries)
        note = f"OI Chg {lead['oi_chg']:,.0f} at {lead['strike']} strike, underlying moved {lead['pct']:+.2f}% same day"
        if other_count:
            note += f" (+{other_count} more strikes covering, total OI Chg {total_oi_chg:,.0f})"
        out.append({
            'signal': 'Signal 1 — Panic Covering',
            'symbol': sym,
            'type': lead['type'],
            'strike': lead['strike'],
            'exp': lead['exp'],
            'direction': direction,
            'premium': None,
            'underlying_price': watchlist[sym]['price'],
            'vol_oi': lead['vol_oi'],
            'note': note,
        })
    return out

def scan_signal4(incoi_rows, watchlist, voloi_map, move_min):
    groups = {}
    for r in incoi_rows:
        sym = r.get('Symbol', '').strip()
        if sym not in watchlist:
            continue
        oi_chg = to_num(r.get('OI Chg'))
        if not (oi_chg > 0):
            continue
        pct = watchlist[sym]['pct']
        opt_type = r.get('Type')
        direction = None
        if opt_type == 'Call' and pct >= move_min:
            direction = 'bullish'   # new calls opened into a rally
        elif opt_type == 'Put' and pct <= -move_min:
            direction = 'bearish'  # new puts opened into a selloff
        if not direction:
            continue
        key = (sym, r.get('Strike'), opt_type, r.get('Exp Date'))
        entry = {
            'symbol': sym,
            'type': opt_type,
            'strike': r.get('Strike'),
            'exp': r.get('Exp Date'),
            'direction': direction,
            'oi_chg': oi_chg,
            'pct': pct,
            'vol_oi': voloi_map.get(key, ''),
        }
        groups.setdefault((sym, direction), []).append(entry)

    out = []
    for (sym, direction), entries in groups.items():
        entries.sort(key=lambda e: e['oi_chg'], reverse=True)  # most positive first
        lead = entries[0]
        other_count = len(entries) - 1
        total_oi_chg = sum(e['oi_chg'] for e in entries)
        note = f"OI Build +{lead['oi_chg']:,.0f} at {lead['strike']} strike, underlying moved {lead['pct']:+.2f}%"
        if other_count:
            note += f" (+{other_count} additional strikes building, total OI Build +{total_oi_chg:,.0f})"
        out.append({
            'signal': 'Signal 4 — Trend Conviction',
            'symbol': sym,
            'type': lead['type'],
            'strike': lead['strike'],
            'exp': lead['exp'],
            'direction': lead['direction'],
            'premium': float('nan'),
            'underlying_price': watchlist[sym]['price'],
            'vol_oi': lead['vol_oi'],
            'note': note,
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--active', required=True)
    ap.add_argument('--flow', required=True)
    ap.add_argument('--decoi', required=True)
    ap.add_argument('--incoi', required=False, help='Increase in Open Interest CSV')
    ap.add_argument('--unusual', required=False)
    ap.add_argument('--liquidity-min', type=float, default=10000)
    ap.add_argument('--premium-min', type=float, default=50000)
    ap.add_argument('--move-min', type=float, default=3)
    ap.add_argument('--out', default=None, help='Optional path to write flagged candidates as CSV')
    args = ap.parse_args()

    active_rows = read_csv(args.active)
    flow_rows = read_csv(args.flow)
    decoi_rows = read_csv(args.decoi)
    incoi_rows = read_csv(args.incoi) if args.incoi else []
    unusual_rows = read_csv(args.unusual) if args.unusual else []

    watchlist = build_watchlist(active_rows, args.liquidity_min)
    voloi_map = build_voloi_map(unusual_rows)

    sig2_and_3 = scan_signal2_and_3(flow_rows, watchlist, voloi_map, args.premium_min)
    sig1 = scan_signal1(decoi_rows, watchlist, voloi_map, args.move_min)
    sig4 = scan_signal4(incoi_rows, watchlist, voloi_map, args.move_min)

    results = sig2_and_3 + sig1 + sig4
    results.sort(key=lambda x: (x['signal'], -(x['premium'] or 0)))
    
    sig3_count = sum(1 for r in sig2_and_3 if 'Signal 3' in r['signal'])
    sig2_count = len(sig2_and_3) - sig3_count

    print(f"Watchlist size (liquidity >= {args.liquidity_min:,.0f}): {len(watchlist)} names")
    print(f"Signal 4 candidates (Trend Build): {len(sig4)}")
    print(f"Signal 3 candidates (Risk Revs): {sig3_count}")
    print(f"Signal 2 candidates (Sweeps): {sig2_count}")
    print(f"Signal 1 candidates (Panic): {len(sig1)}")
    print()

    if args.out:
        out_dir = os.path.dirname(args.out)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

    txt_out = args.out.replace('.csv', '.txt') if args.out else None
    f_txt = open(txt_out, 'w', encoding='utf-8') if txt_out else None

    if f_txt:
        f_txt.write(f"Watchlist size (liquidity >= {args.liquidity_min:,.0f}): {len(watchlist)} names\n")
        f_txt.write(f"Signal 4 candidates (Trend Build): {len(sig4)}\n")
        f_txt.write(f"Signal 3 candidates (Risk Revs): {sig3_count}\n")
        f_txt.write(f"Signal 2 candidates (Sweeps): {sig2_count}\n")
        f_txt.write(f"Signal 1 candidates (Panic): {len(sig1)}\n\n")

    header_line = f"[{'DIR':8}] {'SYMBOL':6} {'TYPE':4} {'STRIKE':>10} exp {'EXP_DATE':10} | SIGNAL | NOTE"
    print(header_line)
    print("-" * 120)
    if f_txt:
        f_txt.write(header_line + "\n")
        f_txt.write("-" * 120 + "\n")

    for r in results:
        line = f"[{r['direction'].upper():8}] {r['symbol']:6} {r['type']:4} {r['strike']:>10} exp {r['exp']} | {r['signal']} | {r['note']}" + (f" | Vol/OI {r['vol_oi']}" if r['vol_oi'] else "")
        print(line)
        if f_txt:
            f_txt.write(line + "\n")

    if f_txt:
        f_txt.close()

    if args.out:
        fieldnames = ['signal', 'symbol', 'type', 'strike', 'exp', 'direction',
                      'premium', 'underlying_price', 'vol_oi', 'note']
        with open(args.out, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r in results:
                w.writerow(r)
        print(f"\nWrote {len(results)} candidates to {args.out}")

    return results


if __name__ == '__main__':
    main()
