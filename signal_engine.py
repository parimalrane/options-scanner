import data_loader

def build_watchlist(active_rows, liquidity_min):
    watchlist = {}
    for r in active_rows:
        sym = r.get('Symbol', '').strip()
        vol = data_loader.to_num(r.get('Options Vol'))
        if sym and vol >= liquidity_min:
            pc = data_loader.to_num(r.get('%Change', '0').replace('%', ''))
            watchlist[sym] = {
                'price': data_loader.to_num(r.get('Latest')),
                'pct_change': pc
            }
    return watchlist

def build_voloi_map(unusual_rows):
    m = {}
    for r in unusual_rows:
        key = (r.get('Symbol'), r.get('Strike'), r.get('Type'), r.get('Exp Date'))
        m[key] = r.get('Vol/OI')
    return m

def get_mid_price(r):
    bid = data_loader.to_num(r.get('Bid'))
    ask = data_loader.to_num(r.get('Ask'))
    if bid == bid and ask == ask:
        return (bid + ask) / 2
    return float('nan')

def process_signal(rows, watchlist, prior_prices, voloi_map, context_flags, moneyness_max, oi_chg_min, signal_type, current_date=None, exclude_same_day=True):
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
        oi_chg = data_loader.to_num(oi_chg_raw)
        
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
        
        moneyness = data_loader.to_num(r.get('Moneyness'))
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
        
        days_to_expiry = 0
        if current_date and exp:
            try:
                from datetime import datetime
                exp_date = datetime.strptime(exp, '%Y-%m-%d')
                days_to_expiry = (exp_date - current_date).days
            except:
                pass
                
        if exclude_same_day and days_to_expiry <= 0:
            continue
        
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
            
        pct_chg = watchlist[sym]['pct_change']
        if abs(pct_chg) <= 0.2:
            price_confirmed = 'neutral'
        elif (direction == 'bullish' and pct_chg > 0.2) or (direction == 'bearish' and pct_chg < -0.2):
            price_confirmed = 'true'
        else:
            price_confirmed = 'false'
            
        notional_value = abs(oi_chg) * mid_today * 100
        
        flag_list = []
        if context_flags:
            if sym in context_flags.get('er', set()): flag_list.append('ER')
            if sym in context_flags.get('ivr_high', set()): flag_list.append('IVR+')
            if sym in context_flags.get('ivrv_high', set()): flag_list.append('OVRP')
            if sym in context_flags.get('ivr_low', set()): flag_list.append('IVR-')
            if sym in context_flags.get('ivrv_low', set()): flag_list.append('UNDP')
            if sym in context_flags.get('uvol', set()): flag_list.append('UVOL')

        entry = {
            'symbol': sym,
            'type': opt_type,
            'strike': strike,
            'exp': exp,
            'direction': direction,
            'oi_chg': oi_chg,
            'price_diff': price_diff,
            'vol_oi': voloi_map.get(key, ''),
            'notional_value': notional_value,
            'days_to_expiry': days_to_expiry,
            'price_confirmed': price_confirmed,
            'flags': ",".join(flag_list)
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
        entries.sort(key=lambda e: e['notional_value'], reverse=True)
        lead = entries[0]
        other_count = len(entries) - 1
        total_oi_chg = sum(e['oi_chg'] for e in entries)
        total_notional = sum(e['notional_value'] for e in entries)
        
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
            '_notional_value': total_notional,
            '_lead_notional': lead['notional_value'],
            'days_to_expiry': lead['days_to_expiry'],
            'price_confirmed': lead['price_confirmed'],
            'flags': lead.get('flags', '')
        })
    return out
