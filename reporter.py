import os
import csv

def evaluate_market_bias(results):
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
            
    return bullish_only, bearish_only, mixed_count, symbols_mixed

def write_diagnostics(stats, args, date_str):
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

    if diag_msgs and getattr(args, 'debug', False):
        print(f"\n=== ANALYZE FLOW DIAGNOSTICS ===")
        for m in diag_msgs:
            print(m)

def print_terminal_tables(results, stats, args, date_str, watchlist, rank):
    bullish_only, bearish_only, mixed_count, symbols_mixed = evaluate_market_bias(results)
    
    top_scan = (
        f"=== {date_str} SCAN ===\n"
        f"Watchlist: {len(watchlist)} | Signals: {len(stats['a_out'])}TMG / {len(stats['b_out'])}TMJ / {len(stats['c_out'])}J+G\n"
        f"Bias: {bullish_only} bullish-only | {bearish_only} bearish-only | {mixed_count} mixed"
    )
    
    legend = (
        "--- LEGEND FOR AI ---\n"
        "SIG Types      : TMG = Short Covering | TMJ = Short Build-Up | J+G = Combo\n"
        "CONF           : TRUE if underlying stock confirmed the directional flow\n"
        "PRICE Δ        : Intraday price change of the options premium\n"
        "(+X, ΣY)       : Breadth: +X identical block trades found | Macro Net: Aggregated total OI volume of Y across all strikes\n"
        "Context Flags  : [IVR+] = High IV Rank (Sell premium) | [OVRP] = IV > RV (Expensive) | [ER] = Imminent Earnings\n"
        "                 [IVR-] = Low IV Rank (Buy premium)   | [UNDP] = IV < RV (Underpriced) | [UVOL] = Unusually High Volume\n"
        "---------------------"
    )

    print(top_scan + "\n\n" + legend + "\n")
    if args.out:
        out_dir = os.path.dirname(args.out)
        if out_dir: os.makedirs(out_dir, exist_ok=True)
    txt_out = args.out.replace('.csv', '.txt') if args.out else None
    f_txt = open(txt_out, 'w', encoding='utf-8') if txt_out else None

    if f_txt:
        f_txt.write(top_scan + "\n\n" + legend + "\n\n")

    results_by_symbol = {}
    for r in results:
        results_by_symbol.setdefault(r['symbol'], []).append(r)

    net_signal = {}
    for sym in symbols_mixed:
        bull_val = sum(abs(r.get('_total_oi_chg', 0)) for r in results_by_symbol[sym] if r['direction'] == 'bullish')
        bear_val = sum(abs(r.get('_total_oi_chg', 0)) for r in results_by_symbol[sym] if r['direction'] == 'bearish')
        net_signal[sym] = bull_val - bear_val

    mixed_syms = sorted(list(symbols_mixed), key=lambda s: net_signal[s], reverse=True)

    def get_sym_order(s):
        return min(rank.get(r['signal'], 99) for r in results_by_symbol[s])

    bullish_syms = sorted(
        [s for s in results_by_symbol if s not in symbols_mixed and results_by_symbol[s][0]['direction'] == 'bullish'],
        key=lambda s: (get_sym_order(s), s)
    )
    bearish_syms = sorted(
        [s for s in results_by_symbol if s not in symbols_mixed and results_by_symbol[s][0]['direction'] == 'bearish'],
        key=lambda s: (get_sym_order(s), s)
    )

    def print_block(syms, header_label):
        if not syms: return
        lbl = f"--- {header_label} ---"
        print(lbl)
        if f_txt: f_txt.write(lbl + "\n")
        
        conf_map = {'true': 'TRUE', 'false': 'FALS', 'neutral': 'NEUT'}
        
        if header_label == "SIDEWAYS":
            table_header = f"{'STOCK':7} | {'DIR':7} | {'SIG':3} | {'TYPE':5} | {'STRIKE':>8} | {'EXP':10} | {'DTE':>3} | {'CONF':>4} | {'NOTIONAL':>10} | {'OI CHG':>10} | {'PRICE Δ':>8}"
        else:
            table_header = f"{'STOCK':7} | {'SIG':3} | {'TYPE':5} | {'STRIKE':>8} | {'EXP':10} | {'DTE':>3} | {'CONF':>4} | {'NOTIONAL':>10} | {'OI CHG':>10} | {'PRICE Δ':>8}"
            
        print(table_header)
        if f_txt: f_txt.write(table_header + "\n")
        
        if header_label == "SIDEWAYS":
            for sym in syms:
                sym_signals = results_by_symbol[sym]
                sym_signals.sort(key=lambda x: (rank.get(x['signal'], 99), x['direction'], x.get('exp', '')))
                
                for r in sym_signals:
                    sym_local = r['symbol']
                    arr = 'BULLISH' if r['direction'] == 'bullish' else 'bearish'
                    code = 'J+G' if 'Signal C' in r['signal'] else ('TMG' if 'Signal A' in r['signal'] else 'TMJ')
                    
                    strike = str(r['strike'])
                    exp = str(r['exp'])
                    
                    oi_chg_str = f"{r.get('_oi_chg', float('nan')):,.0f}" if r.get('_oi_chg') == r.get('_oi_chg') else ""
                    price_diff_str = f"{r.get('_price_diff', float('nan')):+.2f}" if r.get('_price_diff') == r.get('_price_diff') else ""
                    
                    notional_str = f"${int(r.get('_lead_notional', 0)):,}"
                    dte = str(r.get('days_to_expiry', 0))
                    conf = conf_map.get(str(r.get('price_confirmed')), 'NEUT')
                    
                    line = f"{sym_local:7} | {arr:7} | {code:3} | {r['type']:5} | {strike:>8} | {exp:10} | {dte:>3} | {conf:>4} | {notional_str:>10} | {oi_chg_str:>10} | {price_diff_str:>8}"
                    if r.get('_other_count', 0) > 0:
                        line += f"  (+{r['_other_count']}, Σ{r['_total_oi_chg']:,.0f})"
                    if r.get('vol_oi'):
                        line += f"  (Vol/OI {r['vol_oi']})"
                    if r.get('flags'):
                        line += f"  [{r['flags']}]"
                        
                    print(line)
                    if f_txt: f_txt.write(line + "\n")
                    
                net_line = f"{'':7} |         |     |       |          |            |     |      |            | net_signal: | {net_signal[sym]:+,.0f}"
                print(net_line)
                if f_txt: f_txt.write(net_line + "\n")
        else:
            for sym in syms:
                sym_signals = results_by_symbol[sym]
                sym_signals.sort(key=lambda x: (rank.get(x['signal'], 99), x.get('exp', '')))
                
                for r in sym_signals:
                    sym_local = r['symbol']
                    code = 'J+G' if 'Signal C' in r['signal'] else ('TMG' if 'Signal A' in r['signal'] else 'TMJ')
                    
                    strike = str(r['strike'])
                    exp = str(r['exp'])
                    
                    oi_chg_str = f"{r.get('_oi_chg', float('nan')):,.0f}" if r.get('_oi_chg') == r.get('_oi_chg') else ""
                    price_diff_str = f"{r.get('_price_diff', float('nan')):+.2f}" if r.get('_price_diff') == r.get('_price_diff') else ""
                    
                    notional_str = f"${int(r.get('_lead_notional', 0)):,}"
                    dte = str(r.get('days_to_expiry', 0))
                    conf = conf_map.get(str(r.get('price_confirmed')), 'NEUT')
                    
                    line = f"{sym_local:7} | {code:3} | {r['type']:5} | {strike:>8} | {exp:10} | {dte:>3} | {conf:>4} | {notional_str:>10} | {oi_chg_str:>10} | {price_diff_str:>8}"
                    if r.get('_other_count', 0) > 0:
                        line += f"  (+{r['_other_count']}, Σ{r['_total_oi_chg']:,.0f})"
                    if r.get('vol_oi'):
                        line += f"  (Vol/OI {r['vol_oi']})"
                    if r.get('flags'):
                        line += f"  [{r['flags']}]"
                        
                    print(line)
                    if f_txt: f_txt.write(line + "\n")
        
        print()
        if f_txt: f_txt.write("\n")

    print_block(bullish_syms, "BULLISH DIRECTION")
    print_block(bearish_syms, "BEARISH DIRECTION")
    print_block(mixed_syms, "SIDEWAYS")

    tv_lbl = "--- TRADINGVIEW WATCHLIST ---"
    print(tv_lbl)
    if f_txt: f_txt.write(tv_lbl + "\n")
    
    bullish_str = "###BULLISH," + ",".join(bullish_syms) if bullish_syms else "###BULLISH,"
    bearish_str = "###BEARISH," + ",".join(bearish_syms) if bearish_syms else "###BEARISH,"
    mixed_str = "###SIDEWAYS," + ",".join(mixed_syms) if mixed_syms else "###SIDEWAYS,"
    
    for l in [bullish_str, bearish_str, mixed_str]:
        print(l)
        if f_txt: f_txt.write(l + "\n")
        
    print()
    if f_txt: f_txt.write("\n")

    if f_txt:
        f_txt.close()


