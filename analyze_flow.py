import argparse
import data_loader
import signal_engine
import reporter

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

    date_obj = data_loader.extract_file_date(args.active)

    active_rows = data_loader.read_csv(args.active)
    decoi_rows = data_loader.read_csv(args.decoi)
    incoi_rows = data_loader.read_csv(args.incoi) if args.incoi else []
    unusual_rows = data_loader.read_csv(args.unusual) if args.unusual else []

    watchlist = signal_engine.build_watchlist(active_rows, args.liquidity_min)
    voloi_map = signal_engine.build_voloi_map(unusual_rows)

    data_loader.update_snapshot(date_obj, [decoi_rows, incoi_rows, unusual_rows])
    prior_prices = data_loader.load_prior_snapshot(date_obj)

    stats = {
        'a_out': [], 'b_out': [], 'c_out': [],
        'missing_snapshot': prior_prices is None,
        'a_excluded_moneyness': 0, 'a_no_prior': 0,
        'b_excluded_moneyness': 0, 'b_no_prior': 0,
    }

    if prior_prices is not None:
        groups_a, stats_a = signal_engine.process_signal(decoi_rows, watchlist, prior_prices, voloi_map, args.moneyness_max, args.oi_chg_min, 'A')
        groups_b, stats_b = signal_engine.process_signal(incoi_rows, watchlist, prior_prices, voloi_map, args.moneyness_max, args.oi_chg_min, 'B')
        
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
                })

    results = stats['c_out'] + stats['a_out'] + stats['b_out']
    rank = {'Signal C — Confirmed Squeeze Setup': 1, 'Signal A — Short Covering': 2, 'Signal B — Short Build-Up': 3}
    results.sort(key=lambda x: (rank.get(x['signal'], 99), x['symbol']))

    date_str = date_obj.strftime('%Y-%m-%d') if date_obj else 'UNKNOWN'
    
    reporter.write_diagnostics(stats, args, date_str)
    reporter.print_terminal_tables(results, stats, args, date_str, watchlist, rank)

    return results

if __name__ == '__main__':
    main()
