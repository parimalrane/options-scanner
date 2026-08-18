import argparse
import data_loader
import signal_engine
import reporter

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--active', nargs='+', required=True)
    ap.add_argument('--flow', nargs='+', required=False)
    ap.add_argument('--decoi', nargs='+', required=True)
    ap.add_argument('--incoi', nargs='+', required=True)
    ap.add_argument('--unusual', nargs='+', required=True)
    ap.add_argument('--liquidity-min', type=float, default=10000)
    ap.add_argument('--moneyness-max', type=float, default=5.0)
    ap.add_argument('--oi-chg-min', type=float, default=500.0)
    ap.add_argument('--premium-min', type=float, default=50000)
    ap.add_argument('--move-min', type=float, default=3)
    ap.add_argument('--out', default=None)
    ap.add_argument('--debug', action='store_true')
    ap.add_argument('--exclude-same-day', action='store_true', default=True)
    ap.add_argument('--earnings', nargs='*')
    ap.add_argument('--ivr-high', nargs='*')
    ap.add_argument('--ivrv-high', nargs='*')
    ap.add_argument('--ivr-low', nargs='*')
    ap.add_argument('--ivrv-low', nargs='*')
    ap.add_argument('--uvol', nargs='*')
    args = ap.parse_args()

    date_obj = data_loader.extract_file_date(args.active[0])
    
    active_rows = []
    for f in args.active: active_rows.extend(data_loader.read_csv(f))
        
    decoi_rows = []
    for f in args.decoi: decoi_rows.extend(data_loader.read_csv(f))
        
    incoi_rows = []
    if args.incoi:
        for f in args.incoi: incoi_rows.extend(data_loader.read_csv(f))
            
    unusual_rows = []
    if args.unusual:
        for f in args.unusual: unusual_rows.extend(data_loader.read_csv(f))

    watchlist = signal_engine.build_watchlist(active_rows, args.liquidity_min)
    voloi_map = signal_engine.build_voloi_map(unusual_rows)

    data_loader.update_snapshot(date_obj, [decoi_rows, incoi_rows, unusual_rows])
    prior_prices = data_loader.load_prior_snapshot(date_obj)

    context_flags = {'er': set(), 'ivr_high': set(), 'ivrv_high': set(), 'ivr_low': set(), 'ivrv_low': set(), 'uvol': set()}
    if args.earnings:
        for f in args.earnings: context_flags['er'].update(r.get('Symbol') for r in data_loader.read_csv(f) if r.get('Symbol'))
    if args.ivr_high:
        for f in args.ivr_high: context_flags['ivr_high'].update(r.get('Symbol') for r in data_loader.read_csv(f) if r.get('Symbol'))
    if args.ivrv_high:
        for f in args.ivrv_high: context_flags['ivrv_high'].update(r.get('Symbol') for r in data_loader.read_csv(f) if r.get('Symbol'))
    if args.ivr_low:
        for f in args.ivr_low: context_flags['ivr_low'].update(r.get('Symbol') for r in data_loader.read_csv(f) if r.get('Symbol'))
    if args.ivrv_low:
        for f in args.ivrv_low: context_flags['ivrv_low'].update(r.get('Symbol') for r in data_loader.read_csv(f) if r.get('Symbol'))
    if args.uvol:
        for f in args.uvol: context_flags['uvol'].update(r.get('Symbol') for r in data_loader.read_csv(f) if r.get('Symbol'))

    stats = {
        'a_out': [], 'b_out': [], 'c_out': [],
        'missing_snapshot': prior_prices is None,
        'a_excluded_moneyness': 0, 'a_no_prior': 0,
        'b_excluded_moneyness': 0, 'b_no_prior': 0,
    }

    if prior_prices is not None:
        groups_a, stats_a = signal_engine.process_signal(decoi_rows, watchlist, prior_prices, voloi_map, context_flags, args.moneyness_max, args.oi_chg_min, 'A', current_date=date_obj, exclude_same_day=args.exclude_same_day)
        groups_b, stats_b = signal_engine.process_signal(incoi_rows, watchlist, prior_prices, voloi_map, context_flags, args.moneyness_max, args.oi_chg_min, 'B', current_date=date_obj, exclude_same_day=args.exclude_same_day)
        
        stats['a_stats'] = stats_a
        stats['b_stats'] = stats_b
        
        stats['a_out'] = signal_engine.consolidate_groups(groups_a, 'Signal A — Short Covering', watchlist)
        stats['b_out'] = signal_engine.consolidate_groups(groups_b, 'Signal B — Short Build-Up', watchlist)
        
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
                    '_notional_value': 0,
                    '_lead_notional': 0,
                    'days_to_expiry': 0,
                    'price_confirmed': 'neutral',
                    'flags': ''
                })

    for sym_res in stats['c_out']:
        # attempt to steal signal a's notional and confirmation
        for a_res in stats['a_out']:
            if a_res['symbol'] == sym_res['symbol']:
                sym_res['_notional_value'] = a_res['_notional_value']
                sym_res['_lead_notional'] = a_res['_lead_notional']
                sym_res['days_to_expiry'] = a_res['days_to_expiry']
                sym_res['price_confirmed'] = a_res['price_confirmed']
                sym_res['flags'] = a_res.get('flags', '')
                break
                
    results = stats['c_out'] + stats['a_out'] + stats['b_out']
    rank = {'Signal C — Confirmed Squeeze Setup': 1, 'Signal A — Short Covering': 2, 'Signal B — Short Build-Up': 3}
    results.sort(key=lambda x: (rank.get(x['signal'], 99), x['symbol']))

    date_str = date_obj.strftime('%Y-%m-%d') if date_obj else 'UNKNOWN'
    
    reporter.write_diagnostics(stats, args, date_str)
    reporter.print_terminal_tables(results, stats, args, date_str, watchlist, rank)

    return results

if __name__ == '__main__':
    main()
