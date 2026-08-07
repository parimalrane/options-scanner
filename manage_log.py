import argparse
import csv
import os
import sys
import contextlib
import io
from datetime import datetime, timedelta

try:
    import yfinance as yf
except ImportError:
    yf = None

FIELDNAMES = ['date_flagged', 'symbol', 'signal', 'direction', 'strike', 'exp',
              'premium_or_oi', 'underlying_price_at_flag', 'catalyst_note',
              'action_taken', 'price_after_3d', 'price_after_10d', 'outcome']

OUTCOME_THRESHOLD_PCT = 1.0

def load_log(path):
    if not os.path.exists(path):
        return []
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))

def save_log(path, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, '') for k in FIELDNAMES})

def trading_days_between(start_date, end_date):
    days = 0
    d = start_date
    while d < end_date:
        d += timedelta(days=1)
        if d.weekday() < 5:
            days += 1
    return days

def get_price(symbol, err_msgs):
    if yf is None:
        return None
    try:
        f = io.StringIO()
        with contextlib.redirect_stdout(f), contextlib.redirect_stderr(f):
            t = yf.Ticker(symbol)
            hist = t.history(period='5d')
        out = f.getvalue()
        if 'Failed' in out or 'Exception' in out or hist.empty:
            if out.strip():
                err_msgs.append(f"Yahoo lookup error for {symbol}: {out.strip()}")
            else:
                err_msgs.append(f"Yahoo lookup for {symbol} failed (empty history).")
            return None
        return float(hist['Close'].iloc[-1])
    except Exception as e:
        err_msgs.append(f"Yahoo lookup exception for {symbol}: {str(e)}")
        return None

def grade_outcome(direction, price_at_flag, price_now):
    if price_at_flag in (None, '', 0) or price_now is None:
        return 'pending'
    try:
        price_at_flag = float(price_at_flag)
    except ValueError:
        return 'pending'
    if price_at_flag == 0:
        return 'pending'
    pct_move = (price_now - price_at_flag) / price_at_flag * 100
    if direction == 'bullish':
        if pct_move >= OUTCOME_THRESHOLD_PCT: return 'working'
        elif pct_move <= -OUTCOME_THRESHOLD_PCT: return 'failed'
        else: return 'unclear'
    elif direction == 'bearish':
        if pct_move <= -OUTCOME_THRESHOLD_PCT: return 'working'
        elif pct_move >= OUTCOME_THRESHOLD_PCT: return 'failed'
        else: return 'unclear'
    return 'pending'

def append_new_candidates(log_rows, flagged_path, date_flagged, diag_msgs):
    flagged = list(csv.DictReader(open(flagged_path, newline='', encoding='utf-8')))
    existing_keys_map = {(r['date_flagged'], r['symbol'], str(r['strike']).strip(), str(r['exp']).strip(), r['signal']): r for r in log_rows}
    
    added = 0
    for r in flagged:
        key = (date_flagged, r['symbol'], str(r['strike']).strip(), str(r['exp']).strip(), r['signal'])
        if key in existing_keys_map:
            diag_msgs.append(f"Dedup removed existing key: {key}")
            continue
            
        log_rows.append({
            'date_flagged': date_flagged,
            'symbol': r['symbol'],
            'signal': r['signal'],
            'direction': r['direction'],
            'strike': r['strike'],
            'exp': r['exp'],
            'premium_or_oi': r.get('premium') or r.get('note', ''),
            'underlying_price_at_flag': r.get('underlying_price', ''),
            'catalyst_note': '',
            'action_taken': '',
            'price_after_3d': '',
            'price_after_10d': '',
            'outcome': 'pending',
        })
        added += 1
        
    return added

def update_followups(log_rows, today, diag_msgs):
    updated = 0
    failed_lookups = 0
    for r in log_rows:
        try:
            flagged_date = datetime.strptime(r['date_flagged'], '%Y-%m-%d')
        except (ValueError, KeyError):
            continue
        tdays = trading_days_between(flagged_date, today)
        
        needs_update = False
        if tdays >= 3 and not r.get('price_after_3d'):
            needs_update = True
        if tdays >= 10 and not r.get('price_after_10d'):
            needs_update = True
            
        if needs_update:
            price = get_price(r['symbol'], diag_msgs)
            if price is not None:
                if tdays >= 3 and not r.get('price_after_3d'):
                    r['price_after_3d'] = round(price, 2)
                    updated += 1
                if tdays >= 10 and not r.get('price_after_10d'):
                    r['price_after_10d'] = round(price, 2)
                    updated += 1
            else:
                failed_lookups += 1

        latest_price = r.get('price_after_10d') or r.get('price_after_3d')
        if latest_price:
            r['outcome'] = grade_outcome(r.get('direction'), r.get('underlying_price_at_flag'), float(latest_price))
    return updated, failed_lookups

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--flagged', required=False)
    ap.add_argument('--date', required=False)
    ap.add_argument('--log', default='options-log.csv')
    ap.add_argument('--debug', action='store_true')
    args = ap.parse_args()

    today = datetime.now()
    log_rows = load_log(args.log)
    diag_msgs = []
    
    if args.flagged:
        date_flagged = args.date or today.strftime('%Y-%m-%d')
        added = append_new_candidates(log_rows, args.flagged, date_flagged, diag_msgs)
    else:
        added = 0
        date_flagged = args.date or today.strftime('%Y-%m-%d')

    updated, failed_lookups = update_followups(log_rows, today, diag_msgs)

    save_log(args.log, log_rows)

    pending = sum(1 for r in log_rows if r.get('outcome') == 'pending')
    working = sum(1 for r in log_rows if r.get('outcome') == 'working')
    failed = sum(1 for r in log_rows if r.get('outcome') == 'failed')
    unclear = sum(1 for r in log_rows if r.get('outcome') == 'unclear')
    
    # Log: +<N new> | <total rows> total | Working <N> Failed <N> Unclear <N> Pending <N> | <N> lookups failed
    summary_line = f"Log: +{added} | {len(log_rows)} total | Working {working} Failed {failed} Unclear {unclear} Pending {pending} | {failed_lookups} lookups failed"
    # print(summary_line)  # suppress terminal output per request
    
    if diag_msgs:
        diag_path = f"outputs/diagnostics-{date_flagged}.txt"
        os.makedirs("outputs", exist_ok=True)
        with open(diag_path, "a", encoding='utf-8') as f:
            f.write("\n=== MANAGE LOG DIAGNOSTICS ===\n")
            for msg in diag_msgs:
                if args.debug:
                    print(msg)
                f.write(msg + "\n")

if __name__ == '__main__':
    main()
