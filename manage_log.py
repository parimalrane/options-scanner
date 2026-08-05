"""
Options Log Manager
--------------------
Maintains a persistent log.csv locally. Each run:
  1. Appends today's flagged candidates (input: analyze_flow.py's output CSV)
  2. Finds older log entries that are now 3 or 10 *trading days* old
  3. Looks up current prices for those symbols (via yfinance) and fills in
     price_after_3d / price_after_10d
  4. Grades the outcome automatically based on direction vs. price move

No LLM involved in this step — it's pure data lookup and arithmetic.
Requires: pip install yfinance --break-system-packages  (one-time)

Usage:
    python3 manage_log.py --flagged outputs/flagged-XX-XX-XXXX.csv --log options-log.csv
"""

import argparse
import csv
import os
from datetime import datetime, timedelta

try:
    import yfinance as yf
except ImportError:
    yf = None

FIELDNAMES = ['date_flagged', 'symbol', 'signal', 'direction', 'strike', 'exp',
              'premium_or_oi', 'underlying_price_at_flag', 'catalyst_note',
              'action_taken', 'price_after_3d', 'price_after_10d', 'outcome']

OUTCOME_THRESHOLD_PCT = 1.0  # min % move in the predicted direction to call it "working"


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
    """Count weekdays between two dates (ignores holidays, close enough for this)."""
    days = 0
    d = start_date
    while d < end_date:
        d += timedelta(days=1)
        if d.weekday() < 5:
            days += 1
    return days


def get_price(symbol):
    if yf is None:
        return None
    try:
        t = yf.Ticker(symbol)
        hist = t.history(period='5d')
        if hist.empty:
            return None
        return float(hist['Close'].iloc[-1])
    except Exception:
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
        if pct_move >= OUTCOME_THRESHOLD_PCT:
            return 'working'
        elif pct_move <= -OUTCOME_THRESHOLD_PCT:
            return 'failed'
        else:
            return 'unclear'
    elif direction == 'bearish':
        if pct_move <= -OUTCOME_THRESHOLD_PCT:
            return 'working'
        elif pct_move >= OUTCOME_THRESHOLD_PCT:
            return 'failed'
        else:
            return 'unclear'
    return 'pending'


def append_new_candidates(log_rows, flagged_path, date_flagged):
    flagged = list(csv.DictReader(open(flagged_path, newline='', encoding='utf-8')))
    existing_keys_map = {(r['date_flagged'], r['symbol'], str(r['strike']).strip(), str(r['exp']).strip(), r['signal']): r for r in log_rows}
    
    # Also print out a few existing keys to see what they look like
    print("\n--- DIAGNOSTIC: manage_log.py dedup keys ---")
    print(f"Total existing keys in log: {len(existing_keys_map)}")
    if existing_keys_map:
        print("Sample existing key:", list(existing_keys_map.keys())[0])

    added = 0
    for r in flagged:
        # Strip strike and exp just in case they have spaces
        key = (date_flagged, r['symbol'], str(r['strike']).strip(), str(r['exp']).strip(), r['signal'])
        if key in existing_keys_map:
            print(f"DUPLICATE KILLED: {key}")
            print(f"   -> Exact existing row: {existing_keys_map[key]}")
            continue
        else:
            print(f"NEW KEY ADDED: {key}")
            
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
        
    print("--------------------------------------------\n")
    return added


def update_followups(log_rows, today):
    updated = 0
    for r in log_rows:
        try:
            flagged_date = datetime.strptime(r['date_flagged'], '%Y-%m-%d')
        except (ValueError, KeyError):
            continue
        tdays = trading_days_between(flagged_date, today)

        if tdays >= 3 and not r.get('price_after_3d'):
            price = get_price(r['symbol'])
            if price is not None:
                r['price_after_3d'] = round(price, 2)
                updated += 1

        if tdays >= 10 and not r.get('price_after_10d'):
            price = get_price(r['symbol'])
            if price is not None:
                r['price_after_10d'] = round(price, 2)
                updated += 1

        # Grade outcome off whichever checkpoint is most recently available
        latest_price = r.get('price_after_10d') or r.get('price_after_3d')
        if latest_price:
            r['outcome'] = grade_outcome(r.get('direction'), r.get('underlying_price_at_flag'), float(latest_price))
    return updated


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--flagged', required=False, help='Path to today\'s flagged CSV from analyze_flow.py')
    ap.add_argument('--date', required=False, help='Date this batch was flagged, YYYY-MM-DD (defaults to today)')
    ap.add_argument('--log', default='options-log.csv')
    args = ap.parse_args()

    if yf is None:
        print("NOTE: yfinance not installed. Run: pip install yfinance --break-system-packages")
        print("Follow-up price lookups will be skipped until it's installed.\n")

    today = datetime.now()
    log_rows = load_log(args.log)

    if args.flagged:
        date_flagged = args.date or today.strftime('%Y-%m-%d')
        added = append_new_candidates(log_rows, args.flagged, date_flagged)
        print(f"Appended {added} new candidates dated {date_flagged}.")

    updated = update_followups(log_rows, today)
    print(f"Updated {updated} follow-up price fields across {len(log_rows)} total log rows.")

    save_log(args.log, log_rows)
    print(f"Log saved to {args.log}")

    pending = sum(1 for r in log_rows if r.get('outcome') == 'pending')
    working = sum(1 for r in log_rows if r.get('outcome') == 'working')
    failed = sum(1 for r in log_rows if r.get('outcome') == 'failed')
    unclear = sum(1 for r in log_rows if r.get('outcome') == 'unclear')
    print(f"\nOutcome summary — working: {working}  failed: {failed}  unclear: {unclear}  pending: {pending}")


if __name__ == '__main__':
    main()
