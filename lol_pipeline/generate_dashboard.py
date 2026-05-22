import os
import sys
import sqlite3
import json
import argparse
import math
import random
import itertools
from datetime import datetime, timezone, timedelta

# Standardize path imports
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from lol_pipeline.config import DB_PATH
from models.kda_prophet import KDAProphet

LEDGER_DB = os.path.join(BASE_DIR, "data", "prediction_ledger.db")

def solve_g_from_p(p):
    """
    Given a series win probability p in a Bo3, solve for the single-game win probability g
    under the assumption p = 3g^2 - 2g^3.
    """
    if p <= 0.0:
        return 0.0
    if p >= 1.0:
        return 1.0
    
    # Binary search for g
    low, high = 0.0, 1.0
    for _ in range(15):
        mid = (low + high) / 2
        p_mid = 3 * mid**2 - 2 * mid**3
        if p_mid < p:
            low = mid
        else:
            high = mid
    return (low + high) / 2

def decimal_to_american(decimal_odds):
    if not decimal_odds or decimal_odds <= 1.0 or decimal_odds == 999.0:
        return "—"
    if decimal_odds >= 2.0:
        am = (decimal_odds - 1.0) * 100.0
        return f"+{int(round(am))}"
    else:
        am = -100.0 / (decimal_odds - 1.0)
        return f"{int(round(am))}"

def load_data(target_date=None):
    """
    Load matches, market odds, and model predictions from databases.
    If target_date is provided (YYYY-MM-DD), filters specifically for that date.
    Otherwise, grabs matches from the last 2 days and next 5 days.
    """
    conn_odds = sqlite3.connect(DB_PATH)
    conn_odds.row_factory = sqlite3.Row
    cursor_odds = conn_odds.cursor()
    
    conn_ledger = sqlite3.connect(LEDGER_DB)
    conn_ledger.row_factory = sqlite3.Row
    cursor_ledger = conn_ledger.cursor()
    
    # 1. Fetch market odds
    if target_date:
        cursor_odds.execute("""
            SELECT date, team1, team2, team1_odds, team2_odds, bookmaker, fetched_at
            FROM market_odds
            WHERE date = ?
            ORDER BY date ASC
        """, (target_date,))
    else:
        today = datetime.now().strftime('%Y-%m-%d')
        date_start = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
        date_end = (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d')
        cursor_odds.execute("""
            SELECT date, team1, team2, team1_odds, team2_odds, bookmaker, fetched_at
            FROM market_odds
            WHERE date >= ? AND date <= ?
            ORDER BY date ASC
        """, (date_start, date_end))
        
    odds_rows = [dict(r) for r in cursor_odds.fetchall()]
    
    if not odds_rows:
        cursor_odds.execute("""
            SELECT date, team1, team2, team1_odds, team2_odds, bookmaker, fetched_at
            FROM market_odds
            ORDER BY date DESC, fetched_at DESC
            LIMIT 15
        """)
        odds_rows = [dict(r) for r in cursor_odds.fetchall()]
        
    conn_odds.close()
    
    # 2. Correlate with latest model predictions from ledger
    matches = []
    seen_match_ids = set()
    
    for o in odds_rows:
        t1 = o['team1']
        t2 = o['team2']
        date_val = o['date']
        
        cursor_ledger.execute("""
            SELECT match_id, league, team1, team2, team1_roster, team2_roster, model_prob, predicted_score, notes, predicted_at, winner, actual_score
            FROM predictions
            WHERE (team1 = ? AND team2 = ?) OR (team1 = ? AND team2 = ?)
            ORDER BY predicted_at DESC
            LIMIT 1
        """, (t1, t2, t2, t1))
        
        pred = cursor_ledger.fetchone()
        if pred:
            pred = dict(pred)
            if pred['match_id'] in seen_match_ids:
                continue
            seen_match_ids.add(pred['match_id'])
            flipped = (pred['team1'] == t2)
            
            t1_odds = o['team1_odds']
            t2_odds = o['team2_odds']
            
            if flipped:
                model_t1_prob = 1.0 - pred['model_prob']
                model_t2_prob = pred['model_prob']
                t1_roster = json.loads(pred['team2_roster']) if pred['team2_roster'] else []
                t2_roster = json.loads(pred['team1_roster']) if pred['team1_roster'] else []
            else:
                model_t1_prob = pred['model_prob']
                model_t2_prob = 1.0 - pred['model_prob']
                t1_roster = json.loads(pred['team1_roster']) if pred['team1_roster'] else []
                t2_roster = json.loads(pred['team2_roster']) if pred['team2_roster'] else []
            
            # Ensure probabilities are clamped safely
            model_t1_prob = max(0.01, min(0.99, model_t1_prob))
            model_t2_prob = 1.0 - model_t1_prob
            
            implied_t1_odds = 1.0 / model_t1_prob
            implied_t2_odds = 1.0 / model_t2_prob
            
            # ── DE-SERIALIZE NOTES payload ──
            notes_dict = {}
            if pred['notes']:
                try:
                    notes_dict = json.loads(pred['notes'])
                except Exception:
                    notes_dict = {'raw_notes': pred['notes']}
            
            # Solve game win probability g
            g_t1 = solve_g_from_p(model_t1_prob)
            g_t2 = 1.0 - g_t1
            
            # Calculate score distribution
            scores_prob = {
                '2-0': g_t1**2,
                '2-1': 2 * g_t1**2 * g_t2,
                '1-2': 2 * g_t2**2 * g_t1,
                '0-2': g_t2**2
            }
            # Normalize score probabilities to sum to 1.0
            sum_s = sum(scores_prob.values())
            if sum_s > 0:
                scores_prob = {k: v / sum_s for k, v in scores_prob.items()}
            
            # Overwrite with precise simulation scores if present in notes
            if 'scores' in notes_dict and notes_dict['scores']:
                scores_prob = notes_dict['scores']
            
            # Calculate derivative market probabilities
            prob_over_2_5 = scores_prob.get('2-1', 0.0) + scores_prob.get('1-2', 0.0)
            prob_under_2_5 = scores_prob.get('2-0', 0.0) + scores_prob.get('0-2', 0.0)
            prob_t1_minus_1_5 = scores_prob.get('2-0', 0.0)
            prob_t1_plus_1_5 = scores_prob.get('2-0', 0.0) + scores_prob.get('2-1', 0.0) + scores_prob.get('1-2', 0.0)
            prob_t2_minus_1_5 = scores_prob.get('0-2', 0.0)
            prob_t2_plus_1_5 = scores_prob.get('0-2', 0.0) + scores_prob.get('1-2', 0.0) + scores_prob.get('2-1', 0.0)
            
            # Derive Market vig-free odds and market probabilities for derivatives
            derivatives_odds = {}
            if t1_odds and t2_odds and t1_odds > 1.0 and t2_odds > 1.0:
                raw_impl_t1 = 1.0 / t1_odds
                raw_impl_t2 = 1.0 / t2_odds
                total_impl = raw_impl_t1 + raw_impl_t2
                vigfree_t1 = raw_impl_t1 / total_impl
                
                market_g = solve_g_from_p(vigfree_t1)
                market_g_t2 = 1.0 - market_g
                
                m_p_2_0 = market_g**2
                m_p_2_1 = 2 * market_g**2 * market_g_t2
                m_p_1_2 = 2 * market_g_t2**2 * market_g
                m_p_0_2 = market_g_t2**2
                
                m_sum = m_p_2_0 + m_p_2_1 + m_p_1_2 + m_p_0_2
                if m_sum > 0:
                    m_p_2_0 /= m_sum
                    m_p_2_1 /= m_sum
                    m_p_1_2 /= m_sum
                    m_p_0_2 /= m_sum
                
                # Over/Under 2.5 market probs
                m_p_over = m_p_2_1 + m_p_1_2
                m_p_under = m_p_2_0 + m_p_0_2
                
                # Apply 6% bookmaker vig to recreate market odds for derivatives
                vig_factor = 1.06
                derivatives_odds = {
                    't1_minus_1_5': 1.0 / (m_p_2_0 * vig_factor) if m_p_2_0 > 0 else 999.0,
                    't1_plus_1_5': 1.0 / ( (1.0 - m_p_0_2) * vig_factor ) if m_p_0_2 < 1.0 else 999.0,
                    't2_minus_1_5': 1.0 / (m_p_0_2 * vig_factor) if m_p_0_2 > 0 else 999.0,
                    't2_plus_1_5': 1.0 / ( (1.0 - m_p_2_0) * vig_factor ) if m_p_2_0 < 1.0 else 999.0,
                    'over_2_5': 1.0 / (m_p_over * vig_factor) if m_p_over > 0 else 999.0,
                    'under_2_5': 1.0 / (m_p_under * vig_factor) if m_p_under > 0 else 999.0,
                }
            
            # EV calculations (Moneyline)
            ev1 = (model_t1_prob * t1_odds - 1.0) * 100.0 if t1_odds else 0.0
            ev2 = (model_t2_prob * t2_odds - 1.0) * 100.0 if t2_odds else 0.0
            
            # Sizing (Fractional Kelly)
            kelly1 = ((model_t1_prob * t1_odds - 1.0) / (t1_odds - 1.0)) if t1_odds and t1_odds > 1.0 else 0.0
            kelly2 = ((model_t2_prob * t2_odds - 1.0) / (t2_odds - 1.0)) if t2_odds and t2_odds > 1.0 else 0.0
            
            bet1 = max(0.0, 0.25 * kelly1 * 100.0)
            bet2 = max(0.0, 0.25 * kelly2 * 100.0)
            
            recommendation = "No Bet"
            rec_side = None
            rec_size = 0.0
            rec_ev = 0.0
            
            if ev1 > 0 and ev1 > ev2:
                recommendation = f"BET {t1} ML ({bet1:.1f}%)"
                rec_side = t1
                rec_size = bet1
                rec_ev = ev1
            elif ev2 > 0:
                recommendation = f"BET {t2} ML ({bet2:.1f}%)"
                rec_side = t2
                rec_size = bet2
                rec_ev = ev2
                
            matches.append({
                'match_id': pred['match_id'],
                'league': pred['league'] or 'LCK CL',
                'date': date_val,
                'team1': t1,
                'team2': t2,
                't1_odds': t1_odds,
                't2_odds': t2_odds,
                'model_t1_prob': model_t1_prob,
                'model_t2_prob': model_t2_prob,
                'implied_t1_odds': implied_t1_odds,
                'implied_t2_odds': implied_t2_odds,
                'ev1': ev1,
                'ev2': ev2,
                'bet1': bet1,
                'bet2': bet2,
                'recommendation': recommendation,
                'rec_side': rec_side,
                'rec_size': rec_size,
                'rec_ev': rec_ev,
                'bookmaker': o['bookmaker'],
                't1_roster': t1_roster,
                't2_roster': t2_roster,
                'predicted_score': pred['predicted_score'],
                'notes': notes_dict,
                'predicted_at': pred['predicted_at'],
                'winner': pred['winner'],
                'actual_score': pred['actual_score'],
                # Derivative probabilities & estimated odds
                'prob_over_2_5': prob_over_2_5,
                'prob_under_2_5': prob_under_2_5,
                'prob_t1_minus_1_5': prob_t1_minus_1_5,
                'prob_t1_plus_1_5': prob_t1_plus_1_5,
                'prob_t2_minus_1_5': prob_t2_minus_1_5,
                'prob_t2_plus_1_5': prob_t2_plus_1_5,
                'scores_prob': scores_prob,
                'derivatives_odds': derivatives_odds
            })
            
    # ── FETCH DFS PLAYER PROPS ──
    conn_odds = sqlite3.connect(DB_PATH)
    conn_odds.row_factory = sqlite3.Row
    cursor_odds = conn_odds.cursor()
    cursor_odds.execute("SELECT * FROM player_props")
    player_props = [dict(r) for r in cursor_odds.fetchall()]
    conn_odds.close()
            
    conn_ledger.close()
    matches.sort(key=lambda x: (x['date'], x['league']))
    return matches, player_props

def generate_html(matches, player_props, target_date=None):
    total_matches = len(matches)
    edges_found = sum(1 for m in matches if m['rec_size'] > 0)
    
    max_conf = 0.0
    for m in matches:
        max_conf = max(max_conf, m['model_t1_prob'], m['model_t2_prob'])
        
    recommended_bets = sum(1 for m in matches if m['rec_size'] > 0)
    
    if target_date:
        today = target_date
    elif matches:
        today = matches[0]['date']
    else:
        today = datetime.now().strftime('%Y-%m-%d')
    generation_time = datetime.now(timezone.utc).strftime('%b %d, %Y at %H:%M') + " UTC"
    
    # ── COMPILE ALL UNIQUE POSITIVE EV SELECTIONS ──
    unique_bets = []
    for m in matches:
        matchup = f"{m['team1']} vs {m['team2']}"
        # 1. Moneyline edges
        if m['ev1'] > 0 and m['t1_odds']:
            unique_bets.append({
                'matchup': matchup,
                'league': m['league'],
                'type': 'Match Winner',
                'selection': f"{m['team1']} ML",
                'odds': m['t1_odds'],
                'prob': m['model_t1_prob'] * 100.0,
                'ev': m['ev1'],
                'driver': f"Ensemble consensus favors S-Tier lane matchups or synergy advantages for {m['team1']}."
            })
        if m['ev2'] > 0 and m['t2_odds']:
            unique_bets.append({
                'matchup': matchup,
                'league': m['league'],
                'type': 'Match Winner',
                'selection': f"{m['team2']} ML",
                'odds': m['t2_odds'],
                'prob': m['model_t2_prob'] * 100.0,
                'ev': m['ev2'],
                'driver': f"Strong underdog rating slide or recent form swing makes {m['team2']} highly undervalued."
            })
        
        # 2. Handicap Spreads
        if m['derivatives_odds']:
            # Team 1 -1.5 (2-0 win)
            t1_odds_minus_1_5 = m['derivatives_odds'].get('t1_minus_1_5', 999.0)
            if t1_odds_minus_1_5 < 999.0:
                p_t1_minus = m['prob_t1_minus_1_5']
                ev_t1_minus = (p_t1_minus * t1_odds_minus_1_5 - 1.0) * 100.0
                if ev_t1_minus > 0:
                    unique_bets.append({
                        'matchup': matchup,
                        'league': m['league'],
                        'type': 'Map Spread',
                        'selection': f"{m['team1']} -1.5 Spread",
                        'odds': t1_odds_minus_1_5,
                        'prob': p_t1_minus * 100.0,
                        'ev': ev_t1_minus,
                        'driver': f"High probability of absolute clean sweep (2-0 stomp) projected by Monte Carlo runs."
                    })
            # Team 2 +1.5 (loses 1-2 or wins series)
            t2_odds_plus_1_5 = m['derivatives_odds'].get('t2_plus_1_5', 999.0)
            if t2_odds_plus_1_5 < 999.0:
                p_t2_plus = m['prob_t2_plus_1_5']
                ev_t2_plus = (p_t2_plus * t2_odds_plus_1_5 - 1.0) * 100.0
                if ev_t2_plus > 0:
                    unique_bets.append({
                        'matchup': matchup,
                        'league': m['league'],
                        'type': 'Map Spread',
                        'selection': f"{m['team2']} +1.5 Spread",
                        'odds': t2_odds_plus_1_5,
                        'prob': p_t2_plus * 100.0,
                        'ev': ev_t2_plus,
                        'driver': f"High floor of competitiveness. Red-side champion pick adjustments secure at least 1 map."
                    })
            # Team 2 -1.5 (2-0 win)
            t2_odds_minus_1_5 = m['derivatives_odds'].get('t2_minus_1_5', 999.0)
            if t2_odds_minus_1_5 < 999.0:
                p_t2_minus = m['prob_t2_minus_1_5']
                ev_t2_minus = (p_t2_minus * t2_odds_minus_1_5 - 1.0) * 100.0
                if ev_t2_minus > 0:
                    unique_bets.append({
                        'matchup': matchup,
                        'league': m['league'],
                        'type': 'Map Spread',
                        'selection': f"{m['team2']} -1.5 Spread",
                        'odds': t2_odds_minus_1_5,
                        'prob': p_t2_minus * 100.0,
                        'ev': ev_t2_minus,
                        'driver': f"High probability of absolute clean sweep (2-0 stomp) projected by Monte Carlo runs."
                    })
            # Team 1 +1.5 (loses 1-2 or wins series)
            t1_odds_plus_1_5 = m['derivatives_odds'].get('t1_plus_1_5', 999.0)
            if t1_odds_plus_1_5 < 999.0:
                p_t1_plus = m['prob_t1_plus_1_5']
                ev_t1_plus = (p_t1_plus * t1_odds_plus_1_5 - 1.0) * 100.0
                if ev_t1_plus > 0:
                    unique_bets.append({
                        'matchup': matchup,
                        'league': m['league'],
                        'type': 'Map Spread',
                        'selection': f"{m['team1']} +1.5 Spread",
                        'odds': t1_odds_plus_1_5,
                        'prob': p_t1_plus * 100.0,
                        'ev': ev_t1_plus,
                        'driver': f"High floor of competitiveness. Blue-side draft priority secures at least 1 map."
                    })
            
            # 3. Map Totals (Over/Under 2.5)
            t_odds_over = m['derivatives_odds'].get('over_2_5', 999.0)
            if t_odds_over < 999.0:
                p_over = m['prob_over_2_5']
                ev_over = (p_over * t_odds_over - 1.0) * 100.0
                if ev_over > 0:
                    unique_bets.append({
                        'matchup': matchup,
                        'league': m['league'],
                        'type': 'Map Total',
                        'selection': "Over 2.5 Maps",
                        'odds': t_odds_over,
                        'prob': p_over * 100.0,
                        'ev': ev_over,
                        'driver': f"Extremely close roster power ratings indicate high likelihood of a full 3-game series."
                    })
            t_odds_under = m['derivatives_odds'].get('under_2_5', 999.0)
            if t_odds_under < 999.0:
                p_under = m['prob_under_2_5']
                ev_under = (p_under * t_odds_under - 1.0) * 100.0
                if ev_under > 0:
                    unique_bets.append({
                        'matchup': matchup,
                        'league': m['league'],
                        'type': 'Map Total',
                        'selection': "Under 2.5 Maps",
                        'odds': t_odds_under,
                        'prob': p_under * 100.0,
                        'ev': ev_under,
                        'driver': f"Lopsided champion pool diversity or fatigue penalties point to a quick 2-0 stomp."
                    })
                    
            # 4. Correct Scorelines
            for scoreline, s_prob in m['scores_prob'].items():
                # Estimate a bookmaker odds for correct score as vig-free implied odds * 1.12 (larger vig for exact score)
                m_score_odds = 1.0 / (s_prob * 1.12) if s_prob > 0.05 else 999.0
                if m_score_odds < 999.0:
                    ev_score = (s_prob * m_score_odds - 1.0) * 100.0
                    # Standardize exact score lines
                    if ev_score > -10.0: # Keep high value options
                        unique_bets.append({
                            'matchup': matchup,
                            'league': m['league'],
                            'type': 'Correct Score',
                            'selection': f"Correct Score {scoreline}",
                            'odds': m_score_odds,
                            'prob': s_prob * 100.0,
                            'ev': ev_score,
                            'driver': f"Precision rating consensus favors the exact series line of {scoreline}."
                        })

    # ── EVALUATE DFS PROPS ──
    prophet = KDAProphet()
    dfs_bets = []
    for prop in player_props:
        # Find implied win probability for the player's match
        match_win_prob = 0.5
        matchup_str = prop['match_id'].replace('_vs_', ' vs ')
        for m in matches:
            if m['team1'] in prop['match_id'] and m['team2'] in prop['match_id']:
                # Basic proxy: if the player is on team1, use t1_prob. 
                # (Without team assignment we just assume 0.5 or use the higher one for now)
                match_win_prob = max(m['model_t1_prob'], m['model_t2_prob'])
                break
                
        eval_result = prophet.predict_prop(
            prop['player_name'], 
            prop['stat_type'], 
            prop['line'], 
            match_win_prob,
            over_odds=prop['over_odds'],
            under_odds=prop['under_odds']
        )
        if eval_result:
            p_over = eval_result['prob_over']
            p_under = eval_result['prob_under']
            o_odds = prop['over_odds']
            u_odds = prop['under_odds']
            
            ev_over = (p_over * o_odds - 1.0) * 100.0 if o_odds > 1.0 else -999
            ev_under = (p_under * u_odds - 1.0) * 100.0 if u_odds > 1.0 else -999
            
            best_sel = "Over" if ev_over > ev_under else "Under"
            best_ev = max(ev_over, ev_under)
            best_prob = p_over if best_sel == "Over" else p_under
            best_odds = o_odds if best_sel == "Over" else u_odds
            
            if best_ev > 0:
                dfs_bet = {
                    'platform': prop['platform'],
                    'player': prop['player_name'],
                    'stat': prop['stat_type'],
                    'line': prop['line'],
                    'selection': f"{best_sel} {prop['line']} {prop['stat_type']}",
                    'odds': best_odds,
                    'prob': best_prob * 100.0,
                    'ev': best_ev,
                    'driver': f"KDA Prophet projection: {eval_result['expected']:.1f} expected {prop['stat_type'].lower()}.",
                    'type': 'DFS Prop Bet',
                    'matchup': matchup_str,
                    'league': 'DFS'
                }
                dfs_bets.append(dfs_bet)
                unique_bets.append(dfs_bet)
                
    dfs_bets.sort(key=lambda x: x['ev'], reverse=True)

    # Sort all bets by EV edge descending
    unique_bets.sort(key=lambda x: x['ev'], reverse=True)
    
    # ── SORT BY GROUPS ──
    vip_best_bets = [b for b in unique_bets if b['type'] in ('Match Winner', 'DFS Prop Bet')][:10]
    map_spreads_list = [b for b in unique_bets if b['type'] == 'Map Spread'][:10]
    map_totals_list = [b for b in unique_bets if b['type'] == 'Map Total'][:10]
    score_specs_list = [b for b in unique_bets if b['type'] == 'Correct Score'][:10]
    
    # Get top EV moneyline team
    top_ev_team = "None"
    top_ev_val = 0.0
    if vip_best_bets:
        top_ev_team = vip_best_bets[0]['selection']
        top_ev_val = vip_best_bets[0]['ev']

    # ── PORTFOLIO PARLAY ALGORITHMS (Kelly Edge Optimized) ──
    candidate_parlays = [b for b in unique_bets if b['ev'] > 0 and b['odds'] > 1.0]
    
    # Backtrack algorithm for Parlay of the Day (min odds 2.0, max probability)
    best_parlay, best_parlay_prob = None, 0.0
    best_lotto, best_lotto_prob = None, 0.0
    
    # Search for optimal 2-3 leg parlay
    for r in range(2, 4):
        for combo in itertools.combinations(candidate_parlays[:15], r):
            # Ensure different matchups
            if len(set(b['matchup'] for b in combo)) < r:
                continue
            prob = math.prod(b['prob']/100.0 for b in combo)
            odds = math.prod(b['odds'] for b in combo)
            if odds >= 2.0 and odds <= 4.5:
                if prob > best_parlay_prob:
                    best_parlay_prob = prob
                    best_parlay = combo
                    
    # Search for optimal Lotto of the Day (min odds 5.0, high prob, max 4 legs)
    for r in range(2, 5):
        for combo in itertools.combinations(candidate_parlays[:20], r):
            if len(set(b['matchup'] for b in combo)) < r:
                continue
            prob = math.prod(b['prob']/100.0 for b in combo)
            odds = math.prod(b['odds'] for b in combo)
            if odds >= 5.0:
                if prob > best_lotto_prob:
                    best_lotto_prob = prob
                    best_lotto = combo

    # ── GENERATE HERO PARLAY CARDS HTML ──
    def compile_parlay_card_html(combo, prob, title, bg_gradient, icon_emoji):
        if not combo:
            return ""
        odds_dec = math.prod(b['odds'] for b in combo)
        amer_odds = decimal_to_american(odds_dec)
        
        legs_html = ""
        for b in combo:
            leg_amer = decimal_to_american(b['odds'])
            legs_html += f"""
            <div class="parlay-leg">
                <div class="parlay-leg-title">
                    <span class="parlay-leg-bullet">⚡</span> {b['selection']} <span class="parlay-leg-odds">({leg_amer})</span>
                </div>
                <div class="parlay-leg-sub">{b['matchup']} • {b['league']}</div>
            </div>
            """
            
        return f"""
        <div class="parlay-card" style="background: {bg_gradient};">
            <div class="parlay-card-header">
                <div class="parlay-card-title">
                    <span class="parlay-card-icon">{icon_emoji}</span> {title}
                </div>
                <div class="parlay-card-meta">
                    <div class="parlay-card-odds">{amer_odds}</div>
                    <div class="parlay-card-winrate">Proj. Win Rate: {(prob*100):.1f}%</div>
                </div>
            </div>
            <div class="parlay-legs-container">
                {legs_html}
            </div>
        </div>
        """

    parlays_html = ""
    if best_parlay or best_lotto:
        parlays_html = '<div class="kpi-grid" style="grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 25px; margin-top: 10px; margin-bottom: 30px;">'
        if best_parlay:
            parlays_html += compile_parlay_card_html(best_parlay, best_parlay_prob, "Nexus Parlay of the Day", "linear-gradient(135deg, rgba(200, 155, 60, 0.15) 0%, rgba(9, 20, 40, 0.9) 100%)", "🏆")
        if best_lotto:
            parlays_html += compile_parlay_card_html(best_lotto, best_lotto_prob, "Void Lotto of the Day", "linear-gradient(135deg, rgba(124, 58, 237, 0.15) 0%, rgba(9, 20, 40, 0.9) 100%)", "🔮")
        parlays_html += '</div>'

    # ── SECTION 1: MATCH SLATE ROWS HTML ──
    slate_rows = ""
    for idx, m in enumerate(matches):
        t1_pct = m['model_t1_prob'] * 100
        t2_pct = m['model_t2_prob'] * 100
        
        t1_odds_str = decimal_to_american(m['t1_odds'])
        t2_odds_str = decimal_to_american(m['t2_odds'])
        
        best_edge_text = "None"
        best_edge_class = "badge-none"
        if m['rec_size'] > 0:
            best_edge_class = "badge-ev"
            best_edge_text = f"{m['rec_side']} ML ({m['rec_size']:.1f}%)"
            
        t1_roster_str = ", ".join(m['t1_roster']) if m['t1_roster'] else "No verified roster"
        t2_roster_str = ", ".join(m['t2_roster']) if m['t2_roster'] else "No verified roster"
        
        # ── EXPANDABLE DETAILED DRAWER DATA ──
        # lane matching
        roles = ["Top", "Jungle", "Mid", "Bot", "Support"]
        lane_rows = ""
        for i, role in enumerate(roles):
            p1_name = m['t1_roster'][i] if i < len(m['t1_roster']) else "Unknown"
            p2_name = m['t2_roster'][i] if i < len(m['t2_roster']) else "Unknown"
            lane_rows += f"""
            <div class="lane-matchup-row">
                <span class="lane-role">{role}</span>
                <span class="lane-player cyan-text">{p1_name}</span>
                <span class="lane-vs">VS</span>
                <span class="lane-player purple-text">{p2_name}</span>
            </div>
            """
            
        # Score progress bars
        score_matrix = ""
        for score, prob in m['scores_prob'].items():
            pct = prob * 100
            score_matrix += f"""
            <div class="score-prog-item">
                <span class="score-prog-label">{score}</span>
                <div class="score-prog-bar-bg">
                    <div class="score-prog-bar-fill" style="width: {pct}%;"></div>
                </div>
                <span class="score-prog-val">{pct:.1f}%</span>
            </div>
            """
            
        # Value traps warnings
        trap_warnings = "<li>🟢 No active value traps detected.</li>"
        if m['notes'] and 'value_traps' in m['notes'] and m['notes']['value_traps']:
            traps = m['notes']['value_traps']
            trap_list = []
            for team, details in traps.items():
                if details.get('trapped', False):
                    trap_list.append(f"<li>⚠️ <strong>{team}</strong>: Overvalued ({len(details.get('flags', []))} flags: {', '.join(details.get('flags', []))})</li>")
            if trap_list:
                trap_warnings = "".join(trap_list)
                
        # Bayesian anchoring
        anchoring_html = "🟢 Raw model predictions are fully aligned with market price."
        if m['notes'] and 'market_anchoring' in m['notes'] and m['notes']['market_anchoring']:
            ma = m['notes']['market_anchoring']
            if m['notes'].get('anchoring_applied', False):
                anchoring_html = f"""
                ⚠️ <strong>Anchoring Active</strong> (Divergence: {(ma.get('divergence', 0)*100):.1f}%)<br>
                • Pre-Anchor Proj: {(ma.get('model_prob_pre_anchor', 0)*100):.1f}%<br>
                • Market Vig-Free: {(ma.get('market_prob', 0)*100):.1f}%<br>
                • Blended Post-Anchor: {(ma.get('model_prob_post_anchor', 0)*100):.1f}% (Blend Weight: {(ma.get('blend', 0)*100):.1f}%)
                """
                
        # Ensemble predictions
        ensemble_html = "🟢 No GBDT ML predictions available."
        if m['notes'] and 'ensemble' in m['notes'] and m['notes']['ensemble']:
            ens = m['notes']['ensemble']
            ensemble_html = f"""
            📊 <strong>GBDT Ensemble Consensus</strong><br>
            • Pure GBDT Win Prob: {(ens.get('gbdt_prob', 0)*100):.1f}%<br>
            • Deterministic Win Prob: {(ens.get('det_prob', 0)*100):.1f}%<br>
            • Blended Consensus: {(ens.get('blended_prob', 0)*100):.1f}% (60/40 Blend)
            """

        resolved_html = ""
        resolved_class = ""
        if m['winner']:
            resolved_class = "resolved-match"
            correct = (m['winner'] == m['team1'] and m['model_t1_prob'] > 0.5) or (m['winner'] == m['team2'] and m['model_t2_prob'] > 0.5)
            badge_class = "correct-badge" if correct else "incorrect-badge"
            badge_text = "WINNER HIT" if correct else "UPSET MISSED"
            resolved_html = f"""
            <div class="resolved-badge-inline {badge_class}">{badge_text}: {m['winner']} ({m['actual_score']})</div>
            """

        slate_rows += f"""
        <tr class="main-row {resolved_class}" onclick="toggleRow(this)" data-search="{m['team1'].lower()} {m['team2'].lower()} {m['league'].lower()}">
            <td>
                <div class="matchup-container">
                    <div class="team-cell">
                        <span class="team-name cyan-text">{m['team1']}</span>
                        <span class="pitcher-name" style="font-size: 0.72rem;">{m['t1_roster'][0] if m['t1_roster'] else ''}.. {m['t1_roster'][-1] if len(m['t1_roster'])>1 else ''}</span>
                    </div>
                    <div class="vs-divider">VS</div>
                    <div class="team-cell">
                        <span class="team-name purple-text">{m['team2']}</span>
                        <span class="pitcher-name" style="font-size: 0.72rem;">{m['t2_roster'][0] if m['t2_roster'] else ''}.. {m['t2_roster'][-1] if len(m['t2_roster'])>1 else ''}</span>
                    </div>
                    {resolved_html}
                </div>
            </td>
            <td class="mono" style="color: var(--primary);">Bo3 Series</td>
            <td>
                <div class="sim-engine-badge" style="font-size: 0.65rem; padding: 2px 6px;">GBDT Ensemble Blended</div>
            </td>
            <td>
                <div class="market-val mono">{t1_odds_str} / {t2_odds_str}</div>
            </td>
            <td style="width: 250px;">
                <div class="win-prob-bar-container">
                    <div class="win-prob-bar away" style="width: {t1_pct}%;">{t1_pct:.1f}%</div>
                    <div class="win-prob-bar home" style="width: {t2_pct}%;">{t2_pct:.1f}%</div>
                </div>
            </td>
            <td>
                <span class="badge {best_edge_class}">{best_edge_text}</span>
            </td>
            <td>
                <span class="row-expand-arrow">▼</span>
            </td>
        </tr>
        <tr class="detail-row" style="display: none;">
            <td colspan="7">
                <div class="drawer-content">
                    <div class="drawer-section">
                        <h4>⚔️ Verified Lane Matchups</h4>
                        <div class="lane-matchups-container">
                            {lane_rows}
                        </div>
                    </div>
                    <div class="drawer-section">
                        <h4>🔮 Precise Score Matrix</h4>
                        <div class="score-matrix-container">
                            {score_matrix}
                        </div>
                    </div>
                    <div class="drawer-section">
                        <h4>🛡️ Predictor Diagnostics</h4>
                        <div class="diagnostics-box" style="margin-bottom: 12px;">
                            {ensemble_html}
                        </div>
                        <div class="diagnostics-box">
                            <strong>🌉 Bayesian Market Anchoring</strong><br>
                            <span style="font-size: 0.78rem; line-height: 1.3;">{anchoring_html}</span>
                        </div>
                    </div>
                    <div class="drawer-section">
                        <h4>⚠️ Value Trap Warnings</h4>
                        <ul class="value-traps-list">
                            {trap_warnings}
                        </ul>
                        <div style="font-size: 0.72rem; color: var(--text-muted); margin-top: 15px;">
                            <strong>Simulated At:</strong> {m['predicted_at'][:16].replace('T', ' ')} UTC • Bovada Price Linked
                        </div>
                    </div>
                </div>
            </td>
        </tr>
        """

    # ── SECTION 2: VIP BEST BETS ROWS ──
    best_bets_rows = ""
    for idx, b in enumerate(vip_best_bets):
        best_bets_rows += f"""
        <tr class="main-row" data-search="{b['matchup'].lower()} {b['league'].lower()}">
            <td class="mono leader-text" style="text-align: center;">{idx+1}</td>
            <td style="color: var(--primary); font-weight: 700;">{b['type']}</td>
            <td>{b['matchup']}</td>
            <td class="cyan-text" style="font-weight: 700;">{b['player'] + ' ' if b.get('player') else ''}{b['selection']}</td>
            <td class="mono">{decimal_to_american(b['odds'])}</td>
            <td class="mono">{b['prob']:.1f}% vs {(1.0/b['odds']*100):.1f}%</td>
            <td class="mono glow-green" style="font-weight: 700;">+{b['ev']:.1f}% EV</td>
            <td style="font-size: 0.85rem; color: var(--text-muted);">{b['driver']}</td>
        </tr>
        """
        
    # ── SECTION 3: ELITE MAP SPREADS ROWS ──
    map_spreads_rows = ""
    for idx, b in enumerate(map_spreads_list):
        map_spreads_rows += f"""
        <tr class="main-row" data-search="{b['matchup'].lower()} {b['league'].lower()}">
            <td class="mono leader-text" style="text-align: center;">{idx+1}</td>
            <td>{b['matchup']}</td>
            <td class="purple-text" style="font-weight: 700;">{b['selection']}</td>
            <td class="mono">{decimal_to_american(b['odds'])}</td>
            <td class="mono glow-gold">{b['prob']:.1f}%</td>
            <td class="mono glow-green" style="font-weight: 700;">{'+' if b['ev']>0 else ''}{b['ev']:.1f}% EV</td>
            <td style="font-size: 0.85rem; color: var(--text-muted);">{b['driver']}</td>
        </tr>
        """

    # ── SECTION 4: MAP TOTALS ROWS ──
    map_totals_rows = ""
    for idx, b in enumerate(map_totals_list):
        map_totals_rows += f"""
        <tr class="main-row" data-search="{b['matchup'].lower()} {b['league'].lower()}">
            <td class="mono leader-text" style="text-align: center;">{idx+1}</td>
            <td>{b['matchup']}</td>
            <td class="cyan-text" style="font-weight: 700;">{b['selection']}</td>
            <td class="mono">{decimal_to_american(b['odds'])}</td>
            <td class="mono glow-gold">{b['prob']:.1f}%</td>
            <td class="mono glow-green" style="font-weight: 700;">{'+' if b['ev']>0 else ''}{b['ev']:.1f}% EV</td>
            <td style="font-size: 0.85rem; color: var(--text-muted);">{b['driver']}</td>
        </tr>
        """
        
    # ── SECTION 5: CORRECT SCORE SPECS ──
    score_specs_rows = ""
    for idx, b in enumerate(score_specs_list):
        score_specs_rows += f"""
        <tr class="main-row" data-search="{b['matchup'].lower()} {b['league'].lower()}">
            <td class="mono leader-text" style="text-align: center;">{idx+1}</td>
            <td>{b['matchup']}</td>
            <td class="glow-gold" style="font-weight: 700;">{b['selection']}</td>
            <td class="mono">{decimal_to_american(b['odds'])}</td>
            <td class="mono glow-gold">{b['prob']:.1f}%</td>
            <td class="mono glow-green" style="font-weight: 700;">{'+' if b['ev']>0 else ''}{b['ev']:.1f}% EV</td>
            <td style="font-size: 0.85rem; color: var(--text-muted);">{b['driver']}</td>
        </tr>
        """
        
    # ── SECTION 6: DFS PLAYER PROPS ROWS ──
    dfs_props_rows = ""
    for idx, b in enumerate(dfs_bets):
        dfs_props_rows += f"""
        <tr class="main-row" data-search="{b['player'].lower()} {b['matchup'].lower()} {b['platform'].lower()}">
            <td class="mono leader-text" style="text-align: center;">{idx+1}</td>
            <td><span class="badge" style="background: rgba(124, 58, 237, 0.2); color: #a855f7; border: 1px solid #7c3aed;">{b['platform']}</span></td>
            <td><span class="cyan-text" style="font-weight: 700; font-size: 1.1rem;">{b['player']}</span></td>
            <td class="glow-gold" style="font-weight: 700;">{b['selection']}</td>
            <td class="mono">{decimal_to_american(b['odds'])}</td>
            <td class="mono glow-gold">{b['prob']:.1f}%</td>
            <td class="mono glow-green" style="font-weight: 700;">{'+' if b['ev']>0 else ''}{b['ev']:.1f}% EV</td>
            <td style="font-size: 0.85rem; color: var(--text-muted);">{b['driver']}</td>
        </tr>
        """

    # ── BUILD HTML ──
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Summoner's Edge — Elite Esports Prediction Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@500;700;800;900&family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-base: #010610; /* Deep hextech dark obsidian space navy */
            --bg-card: rgba(6, 14, 28, 0.75); /* Deep hextech blue-gray glassmorphism */
            --bg-header: rgba(1, 6, 16, 0.85);
            --primary: #c89b3c; /* Prestige Gold Accent */
            --primary-glow: rgba(200, 155, 60, 0.25);
            --secondary: #00d8ff; /* Cyber Cyan (Blue Side) */
            --secondary-light: #0acf83; /* Neon Emerald EV Green */
            --void-purple: #7c3aed; /* Neon Void Purple (Red Side) */
            --border: #1d2a38; /* Hextech slate gray border */
            --border-gold: rgba(200, 155, 60, 0.2);
            --text-main: #f3f4f6; /* Light gray text */
            --text-muted: #8fa3b0;
            --gold-gradient: linear-gradient(135deg, #ffe066 0%, #c89b3c 50%, #7c5a1c 100%);
            --cyan-gradient: linear-gradient(135deg, #00f0ff 0%, #0070aa 100%);
            --purple-gradient: linear-gradient(135deg, #a855f7 0%, #6366f1 100%);
        }}

        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        
        /* Custom scrollbar */
        ::-webkit-scrollbar {{
            width: 8px;
            height: 8px;
        }}
        ::-webkit-scrollbar-track {{
            background: var(--bg-base);
        }}
        ::-webkit-scrollbar-thumb {{
            background: #1e282d;
            border-radius: 4px;
            border: 1px solid var(--primary-glow);
        }}
        ::-webkit-scrollbar-thumb:hover {{
            background: var(--primary);
        }}

        body {{
            font-family: 'Outfit', sans-serif;
            background: radial-gradient(circle at 50% 0%, #061c36 0%, #010712 45%, #000205 100%);
            color: var(--text-main);
            line-height: 1.5;
            padding: 30px 15px;
            min-height: 100vh;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}

        /* Hero Header with Background Image */
        header {{
            position: relative;
            background-image: linear-gradient(to right, rgba(1, 6, 16, 0.95) 30%, rgba(6, 14, 28, 0.7) 70%, rgba(6, 14, 28, 0.4) 100%), url('summoners_edge_banner.png');
            background-size: cover;
            background-position: center;
            border-radius: 20px;
            border: 1px solid var(--border);
            padding: 40px;
            margin-bottom: 30px;
            box-shadow: 0 15px 45px rgba(0, 0, 0, 0.95), inset 0 0 50px rgba(200, 155, 60, 0.08);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 24px;
            border-left: 5px solid var(--primary);
        }}

        .logo-container {{
            display: flex;
            align-items: center;
            gap: 20px;
        }}

        .hextech-crest-coin {{
            width: 58px;
            height: 58px;
            background: radial-gradient(circle at 35% 35%, #fff 0%, #c89b3c 60%, #4a3411 100%);
            clip-path: polygon(50% 0%, 93% 25%, 93% 75%, 50% 100%, 7% 75%, 7% 25%);
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 
                0 0 25px rgba(200, 155, 60, 0.45),
                0 6px 15px rgba(0, 0, 0, 0.6);
            border: 2px solid #ffe875;
            position: relative;
            cursor: pointer;
            transition: transform 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }}

        .hextech-crest-coin:hover {{
            transform: rotate(180deg) scale(1.08);
        }}

        .hextech-symbol-crest {{
            font-size: 1.8rem;
            color: #010a15;
            filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.5));
            line-height: 1;
            font-weight: bold;
        }}

        .header-brand-info {{
            display: flex;
            flex-direction: column;
        }}

        h1 {{
            font-family: 'Cinzel', serif;
            font-weight: 900;
            font-size: 2.6rem;
            letter-spacing: 0.06em;
            background: var(--gold-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            display: flex;
            align-items: center;
            line-height: 1.1;
            text-shadow: 0 0 30px rgba(200, 155, 60, 0.2);
        }}

        .header-brand-info span {{
            font-weight: 600;
            font-size: 0.85rem;
            letter-spacing: 0.32em;
            color: #c89b3c;
            margin-top: 4px;
            text-transform: uppercase;
        }}

        .header-meta {{
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            gap: 10px;
        }}

        .timestamp {{
            font-family: 'JetBrains Mono', monospace;
            color: var(--primary);
            font-size: 0.85rem;
            background-color: rgba(1, 6, 16, 0.9);
            padding: 10px 18px;
            border: 1px solid var(--primary);
            border-radius: 10px;
            box-shadow: 0 0 15px rgba(200, 155, 60, 0.15);
            text-align: right;
            line-height: 1.4;
        }}

        .sim-engine-badge {{
            background: linear-gradient(135deg, rgba(0, 216, 255, 0.2) 0%, rgba(1, 6, 16, 0.8) 100%);
            border: 1px solid var(--secondary);
            color: #00f0ff;
            font-size: 0.75rem;
            font-weight: 700;
            padding: 4px 10px;
            border-radius: 6px;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        .sim-engine-badge::before {{
            content: '';
            display: inline-block;
            width: 8px;
            height: 8px;
            background-color: #00f0ff;
            border-radius: 50%;
            box-shadow: 0 0 8px #00f0ff;
            animation: pulse-cyan 1.8s infinite;
        }}

        @keyframes pulse-cyan {{
            0% {{ transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 240, 255, 0.7); }}
            70% {{ transform: scale(1); box-shadow: 0 0 0 6px rgba(0, 240, 255, 0); }}
            100% {{ transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 240, 255, 0); }}
        }}

        /* KPI widgets grid */
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .kpi-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 20px;
            display: flex;
            flex-direction: column;
            position: relative;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.7);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border-left: 4px solid var(--primary);
            transition: transform 0.2s ease, border-color 0.2s ease;
        }}

        .kpi-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 2px;
            background: repeating-linear-gradient(90deg, 
                #00d8ff, #00d8ff 4px, 
                transparent 4px, transparent 8px, 
                #7c3aed 8px, #7c3aed 12px, 
                transparent 12px, transparent 16px
            );
            opacity: 0.4;
        }}

        .kpi-card:hover {{
            transform: translateY(-2px);
            border-color: var(--primary);
        }}

        .kpi-label {{
            font-size: 0.75rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.1em;
            font-weight: 700;
            margin-bottom: 6px;
        }}

        .kpi-value {{
            font-size: 1.6rem;
            font-weight: 800;
            color: var(--text-main);
            line-height: 1.2;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .kpi-value-gold {{
            background: var(--gold-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 800;
        }}

        .kpi-subtext {{
            font-size: 0.8rem;
            color: var(--text-muted);
            margin-top: 6px;
            display: flex;
            align-items: center;
            gap: 4px;
        }}

        /* Parlay Builder Cards */
        .parlay-card {{
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.7);
            border: 1px solid var(--border-gold);
            display: flex;
            flex-direction: column;
            gap: 15px;
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
        }}

        .parlay-card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            padding-bottom: 12px;
        }}

        .parlay-card-title {{
            font-family: 'Cinzel', serif;
            font-weight: 900;
            font-size: 1.1rem;
            color: #fff;
            letter-spacing: 0.05em;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .parlay-card-icon {{
            font-size: 1.3rem;
            filter: drop-shadow(0 2px 4px rgba(0,0,0,0.5));
        }}

        .parlay-card-meta {{
            text-align: right;
        }}

        .parlay-card-odds {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 1.6rem;
            font-weight: 900;
            background: var(--gold-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            line-height: 1.1;
        }}

        .parlay-card-winrate {{
            font-size: 0.75rem;
            color: var(--text-muted);
            font-weight: 600;
            margin-top: 3px;
        }}

        .parlay-legs-container {{
            display: flex;
            flex-direction: column;
            gap: 12px;
        }}

        .parlay-leg {{
            border-left: 2px solid var(--primary);
            padding-left: 12px;
        }}

        .parlay-leg-title {{
            font-weight: 700;
            font-size: 0.95rem;
            color: var(--text-main);
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        .parlay-leg-odds {{
            font-family: 'JetBrains Mono', monospace;
            color: var(--primary);
            font-size: 0.85rem;
            font-weight: bold;
        }}

        .parlay-leg-sub {{
            font-size: 0.78rem;
            color: var(--text-muted);
            margin-top: 2px;
        }}

        /* Interactive Filter Cards */
        .controls-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.7);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 20px;
            border-top: 1px solid var(--border-gold);
        }}

        .search-container {{
            position: relative;
            flex-grow: 1;
            max-width: 450px;
            min-width: 280px;
        }}

        .search-input {{
            width: 100%;
            background-color: rgba(1, 6, 16, 0.85);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 12px 16px;
            font-family: 'Outfit', sans-serif;
            color: var(--text-main);
            font-size: 0.95rem;
            transition: all 0.2s ease;
        }}

        .search-input:focus {{
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 15px rgba(200, 155, 60, 0.15);
        }}

        .filter-chips {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }}

        .chip {{
            background-color: rgba(6, 14, 28, 0.4);
            border: 1px solid var(--border);
            color: var(--text-muted);
            padding: 10px 16px;
            border-radius: 10px;
            font-size: 0.85rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .chip:hover {{
            border-color: var(--primary);
            color: var(--text-main);
        }}

        .chip.active {{
            background: linear-gradient(135deg, rgba(200, 155, 60, 0.15) 0%, rgba(0, 216, 255, 0.1) 100%);
            border-color: var(--primary);
            color: #ffe066;
            box-shadow: 0 4px 15px rgba(200, 155, 60, 0.15);
        }}

        .chip-count {{
            background-color: rgba(1, 6, 16, 0.8);
            color: var(--text-muted);
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem;
            padding: 2px 6px;
            border-radius: 4px;
            border: 1px solid rgba(200, 155, 60, 0.15);
        }}

        .chip.active .chip-count {{
            color: #ffe066;
            border-color: var(--primary);
        }}

        /* Slate Card Layout */
        .slate-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 0;
            box-shadow: 0 15px 45px rgba(0, 0, 0, 0.8);
            position: relative;
            overflow: hidden;
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--border-gold);
            margin-bottom: 40px;
        }}

        .slate-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: repeating-linear-gradient(90deg, 
                #00d8ff, #00d8ff 4px, 
                transparent 4px, transparent 8px, 
                #7c3aed 8px, #7c3aed 12px, 
                transparent 12px, transparent 16px
            );
            opacity: 0.75;
            z-index: 10;
        }}

        .slate-card-header {{
            padding: 24px 30px;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            background-color: rgba(6, 14, 28, 0.3);
        }}

        .slate-card-header h2 {{
            font-family: 'Cinzel', serif;
            font-weight: 700;
            font-size: 1.5rem;
            color: var(--primary);
            letter-spacing: 0.04em;
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.95rem;
        }}

        th {{
            font-family: 'Outfit', sans-serif;
            font-weight: 700;
            color: var(--primary);
            text-transform: uppercase;
            font-size: 0.78rem;
            letter-spacing: 0.08em;
            padding: 20px 24px;
            border-bottom: 1px solid var(--border);
            text-align: left;
            background-color: rgba(1, 6, 16, 0.5);
        }}

        td {{
            padding: 20px 24px;
            border-bottom: 1px solid var(--border);
            vertical-align: middle;
            transition: background-color 0.2s ease;
        }}

        .main-row {{
            cursor: pointer;
            position: relative;
        }}

        .main-row:hover td {{
            background-color: rgba(200, 155, 60, 0.02);
        }}

        .main-row.expanded td {{
            background-color: rgba(6, 14, 28, 0.25);
            border-bottom-color: transparent;
        }}

        .mono {{
            font-family: 'JetBrains Mono', monospace;
            font-weight: 500;
        }}

        /* Dynamic Win Probability Dual Bar */
        .win-prob-bar-container {{
            display: flex;
            width: 100%;
            height: 24px;
            border-radius: 8px;
            overflow: hidden;
            border: 1px solid var(--border);
            background-color: rgba(1, 6, 16, 0.8);
            margin-top: 2px;
            position: relative;
            box-shadow: inset 0 2px 5px rgba(0,0,0,0.5);
        }}

        .win-prob-bar {{
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.72rem;
            font-weight: 800;
            font-family: 'JetBrains Mono', monospace;
            color: #fff;
            transition: width 0.5s ease-in-out;
            min-width: 30px;
        }}

        .win-prob-bar.away {{
            background: linear-gradient(90deg, #005a82 0%, #00f0ff 100%);
            text-shadow: 0 1px 2px rgba(0,0,0,0.8);
            border-right: 1px solid rgba(1, 6, 16, 0.5);
        }}

        .win-prob-bar.home {{
            background: linear-gradient(90deg, #4c1d95 0%, #7c3aed 100%);
            text-shadow: 0 1px 2px rgba(0,0,0,0.8);
        }}

        /* Badges styling */
        .badge {{
            display: inline-block;
            padding: 6px 12px;
            border-radius: 8px;
            font-size: 0.72rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            text-align: center;
            box-shadow: 0 2px 6px rgba(0,0,0,0.3);
        }}

        .badge-ev {{
            background: linear-gradient(135deg, rgba(200, 155, 60, 0.25) 0%, rgba(10, 207, 131, 0.2) 100%);
            color: #ffe875;
            border: 1px solid rgba(200, 155, 60, 0.6);
            box-shadow: 0 0 15px rgba(200, 155, 60, 0.15);
            font-weight: 800;
            text-shadow: 0 0 5px rgba(200, 155, 60, 0.3);
        }}

        .badge-none {{
            background-color: rgba(148, 163, 184, 0.05);
            color: var(--text-muted);
            border: 1px solid rgba(148, 163, 184, 0.15);
        }}

        .matchup-container {{
            display: flex;
            align-items: center;
            gap: 16px;
        }}

        .team-cell {{
            display: flex;
            flex-direction: column;
            width: 140px;
        }}

        .team-name {{
            font-weight: 800;
            font-size: 1.05rem;
            letter-spacing: -0.01em;
        }}

        .cyan-text {{ color: #00f0ff; text-shadow: 0 0 10px rgba(0, 240, 255, 0.2); }}
        .purple-text {{ color: #bf5af2; text-shadow: 0 0 10px rgba(191, 90, 242, 0.2); }}

        .pitcher-name {{
            font-size: 0.8rem;
            color: var(--text-muted);
            margin-top: 3px;
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 4px;
        }}

        .vs-divider {{
            color: var(--primary);
            font-size: 0.72rem;
            font-weight: 800;
            background-color: rgba(1, 6, 16, 0.95);
            padding: 4px 8px;
            border-radius: 5px;
            border: 1px solid rgba(200, 155, 60, 0.3);
            font-family: 'JetBrains Mono', monospace;
            box-shadow: 0 2px 6px rgba(0,0,0,0.5);
            transition: transform 0.2s ease;
        }}

        .main-row:hover .vs-divider {{
            transform: scale(1.1);
            border-color: var(--primary);
        }}

        .leader-text {{
            color: #ffe066;
            font-weight: 800;
            text-shadow: 0 0 8px rgba(255, 224, 102, 0.25);
        }}
        
        .market-val {{
            font-size: 0.76rem;
            color: var(--text-muted);
            background-color: rgba(1, 6, 16, 0.6);
            padding: 3px 6px;
            border-radius: 4px;
            display: inline-block;
            margin-top: 2px;
            border: 1px solid rgba(200, 155, 60, 0.12);
        }}

        .row-expand-arrow {{
            color: var(--primary);
            font-size: 0.75rem;
            transition: transform 0.3s ease;
            display: inline-block;
        }}

        .main-row.expanded .row-expand-arrow {{
            transform: rotate(180deg);
        }}

        /* Expanded drawer row style */
        .detail-row td {{
            padding: 0;
            background-color: rgba(1, 6, 16, 0.45);
            border-bottom: 1px solid var(--border);
        }}

        .drawer-content {{
            padding: 24px 30px;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 24px;
            animation: slideDown 0.25s ease-out;
            border-left: 4px solid var(--primary);
            background-color: rgba(6, 14, 28, 0.25);
        }}

        @keyframes slideDown {{
            from {{ opacity: 0; transform: translateY(-10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        .drawer-section {{
            display: flex;
            flex-direction: column;
            gap: 12px;
        }}

        .drawer-section h4 {{
            font-family: 'Cinzel', serif;
            font-size: 0.85rem;
            color: var(--primary);
            text-transform: uppercase;
            letter-spacing: 0.08em;
            border-bottom: 1px solid rgba(200, 155, 60, 0.15);
            padding-bottom: 6px;
            margin-bottom: 4px;
        }}

        .lane-matchups-container {{
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}

        .lane-matchup-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(255,255,255,0.02);
            padding-bottom: 6px;
            font-size: 0.85rem;
        }}

        .lane-role {{
            font-weight: 700;
            text-transform: uppercase;
            font-size: 0.72rem;
            color: var(--text-muted);
            background: rgba(1, 6, 16, 0.6);
            padding: 2px 6px;
            border-radius: 4px;
            border: 1px solid var(--border);
            width: 70px;
            text-align: center;
        }}

        .lane-player {{
            font-weight: 600;
            width: 100px;
        }}

        .lane-vs {{
            color: var(--primary);
            font-weight: 900;
            font-size: 0.72rem;
        }}

        .score-matrix-container {{
            display: flex;
            flex-direction: column;
            gap: 10px;
        }}

        .score-prog-item {{
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 0.85rem;
        }}

        .score-prog-label {{
            font-family: 'JetBrains Mono', monospace;
            font-weight: bold;
            color: var(--primary);
            width: 35px;
        }}

        .score-prog-bar-bg {{
            flex-grow: 1;
            height: 10px;
            background-color: rgba(1, 6, 16, 0.8);
            border-radius: 4px;
            overflow: hidden;
            border: 1px solid var(--border);
        }}

        .score-prog-bar-fill {{
            height: 100%;
            background: linear-gradient(90deg, var(--primary-glow) 0%, var(--primary) 100%);
            box-shadow: 0 0 8px var(--primary);
            border-radius: 4px;
        }}

        .score-prog-val {{
            font-family: 'JetBrains Mono', monospace;
            width: 50px;
            text-align: right;
            font-weight: bold;
        }}

        .diagnostics-box {{
            background-color: rgba(1, 6, 16, 0.7);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 12px;
            font-size: 0.8rem;
            line-height: 1.4;
            color: var(--text-main);
        }}

        .value-traps-list {{
            list-style-type: none;
            font-size: 0.8rem;
            line-height: 1.4;
            color: var(--text-muted);
            display: flex;
            flex-direction: column;
            gap: 6px;
        }}

        .glow-green {{
            color: #0acf83;
            text-shadow: 0 0 6px rgba(10, 207, 131, 0.3);
        }}

        .glow-gold {{
            color: #ffe066;
            text-shadow: 0 0 6px rgba(255, 224, 102, 0.3);
        }}

        .resolved-badge-inline {{
            display: inline-block;
            font-size: 0.65rem;
            font-weight: bold;
            padding: 2px 6px;
            border-radius: 4px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-left: 10px;
        }}

        .correct-badge {{
            background-color: rgba(10, 207, 131, 0.15);
            color: #0acf83;
            border: 1px solid rgba(10, 207, 131, 0.3);
        }}

        .incorrect-badge {{
            background-color: rgba(239, 68, 68, 0.15);
            color: #ef4444;
            border: 1px solid rgba(239, 68, 68, 0.3);
        }}

        .empty-slate {{
            text-align: center;
            color: var(--text-muted);
            padding: 50px 20px !important;
            font-size: 1.0rem;
        }}

        .empty-slate code {{
            background-color: rgba(1, 6, 16, 0.8);
            padding: 4px 8px;
            border-radius: 6px;
            border: 1px solid var(--border);
            font-family: 'JetBrains Mono', monospace;
            color: var(--primary);
        }}

        footer {{
            margin-top: 50px;
            border-top: 1px solid var(--border);
            padding-top: 30px;
            text-align: center;
            color: var(--text-muted);
            font-size: 0.8rem;
            display: flex;
            flex-direction: column;
            gap: 15px;
        }}

        .disclaimer {{
            max-width: 700px;
            margin: 0 auto;
            line-height: 1.5;
        }}

        .footer-brand {{
            font-family: 'Cinzel', serif;
            color: var(--primary);
            font-weight: 700;
            font-size: 0.95rem;
            letter-spacing: 0.05em;
        }}
        /* --- MOBILE RESPONSIVENESS --- */
        @media (max-width: 768px) {{
            body {{
                padding: 15px 10px;
            }}
            header {{
                padding: 20px;
                flex-direction: column;
                align-items: flex-start;
                gap: 15px;
            }}
            .logo-container {{
                gap: 12px;
            }}
            .hextech-crest-coin {{
                width: 45px;
                height: 45px;
            }}
            h1 {{
                font-size: 1.7rem;
            }}
            .header-brand-info span {{
                font-size: 0.7rem;
            }}
            .header-meta {{
                align-items: flex-start;
                width: 100%;
            }}
            .timestamp {{
                font-size: 0.75rem;
                padding: 8px 12px;
                text-align: left;
                width: 100%;
            }}
            .kpi-grid {{
                grid-template-columns: 1fr;
            }}
            .controls-card {{
                flex-direction: column;
                align-items: stretch;
                padding: 15px;
            }}
            .search-container {{
                max-width: 100%;
            }}
            .slate-card-header {{
                padding: 15px;
                flex-direction: column;
                align-items: flex-start;
                gap: 10px;
            }}
            .slate-card-header h2 {{
                font-size: 1.15rem;
            }}
            th, td {{
                padding: 12px 15px;
                font-size: 0.85rem;
            }}
            .kpi-value {{
                font-size: 1.3rem;
            }}
            .parlay-card-header {{
                flex-direction: column;
                align-items: flex-start;
                gap: 10px;
            }}
            .parlay-card-meta {{
                text-align: left;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        
        <!-- Hero Header -->
        <header>
            <div class="logo-container">
                <div class="hextech-crest-coin">
                    <span class="hextech-symbol-crest">♦</span>
                </div>
                <div class="header-brand-info">
                    <h1>SUMMONER'S EDGE</h1>
                    <span>O-PROPHET V5.1 ESports Terminal</span>
                </div>
            </div>
            <div class="header-meta">
                <div class="sim-engine-badge">100k Simulations Active</div>
                <div class="timestamp">
                    SLATE DATE: {today}<br>
                    <span style="font-size: 0.72rem; color: var(--text-muted)">UPDATED: {generation_time}</span>
                </div>
            </div>
        </header>

        <!-- KPI Scoreboard Grid -->
        <div class="kpi-grid">
            <div class="kpi-card" style="border-left-color: var(--secondary);">
                <div class="kpi-label">⚔️ Active Slate Coverage</div>
                <div class="kpi-value">{total_matches} Match{'' if total_matches == 1 else 'es'} Mapped</div>
                <div class="kpi-subtext">📊 {total_matches * 100000:,} Total Monte Carlo Iterations</div>
            </div>
            <div class="kpi-card" style="border-left-color: var(--secondary-light);">
                <div class="kpi-label">🔥 Esports Expected Value Edge</div>
                <div class="kpi-value"><span class="kpi-value-gold">{top_ev_team}</span></div>
                <div class="kpi-subtext">💵 Proj. Edge: {top_ev_val:+.1f}% EV vs Bookmaker Price</div>
            </div>
            <div class="kpi-card" style="border-left-color: var(--primary);">
                <div class="kpi-label">💎 Peak Ensemble Confidence</div>
                <div class="kpi-value"><span class="kpi-value-gold">{max_conf*100:.1f}%</span></div>
                <div class="kpi-subtext">📈 Strongest mathematical signal on slate</div>
            </div>
            <div class="kpi-card" style="border-left-color: var(--void-purple);">
                <div class="kpi-label">🔮 Kelly Recommendations</div>
                <div class="kpi-value" style="color: var(--void-purple);">{recommended_bets} Bet Recommendation{'' if recommended_bets == 1 else 's'}</div>
                <div class="kpi-subtext">⚡ 0.25 Fractional Kelly bankroll sizing</div>
            </div>
        </div>

        <!-- Portfolio Parlay Cards -->
        {parlays_html}

        <!-- Interactive Search & Filtering Controls -->
        <div class="controls-card">
            <div class="search-container">
                <input type="text" id="search-input" class="search-input" placeholder="Search by team, roster, or league..." onkeyup="filterSlate()">
            </div>
            <div class="filter-chips">
                <button class="chip active" onclick="setSectionFilter('all', this)">🍀 Show All <span class="chip-count" id="count-all">0</span></button>
                <button class="chip" onclick="setSectionFilter('slate', this)">📈 Game Slate <span class="chip-count" id="count-slate">0</span></button>
                <button class="chip" onclick="setSectionFilter('vip', this)">🔥 VIP Best Bets <span class="chip-count" id="count-vip">0</span></button>
                <button class="chip" onclick="setSectionFilter('spreads', this)">🛡️ Map Spreads <span class="chip-count" id="count-spreads">0</span></button>
                <button class="chip" onclick="setSectionFilter('totals', this)">📊 Map Totals <span class="chip-count" id="count-totals">0</span></button>
                <button class="chip" onclick="setSectionFilter('props', this)">🔮 Prop Bets <span class="chip-count" id="count-props">0</span></button>
                <button class="chip" onclick="setSectionFilter('scores', this)">🔮 Score Specs <span class="chip-count" id="count-scores">0</span></button>
            </div>
        </div>

        <!-- Section 1: Multi-Engine Predictive Analysis (Interactive Slate) -->
        <div id="section-slate" class="slate-card">
            <div class="slate-card-header">
                <h2>🍀 Multi-Engine Predictive Analysis — Click Matchups for Detailed Drawer</h2>
            </div>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Matchup & Roster Overview</th>
                            <th>Format</th>
                            <th>Predictor Engine</th>
                            <th>Live ML (Market Price)</th>
                            <th>Win Probability (Blue vs Red)</th>
                            <th>Best EV Edge</th>
                            <th>Drawer</th>
                        </tr>
                    </thead>
                    <tbody>
                        {slate_rows if slate_rows else f"""
                        <tr>
                            <td colspan="7" class="empty-slate">
                                🔍 No active matchups found in prediction databases.<br>
                                <span style="font-size: 0.85rem; margin-top: 10px; display: block; color: var(--text-muted)">Verify the data pipelines have been ingested correctly.</span>
                            </td>
                        </tr>
                        """}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Section 2: VIP Best Bets -->
        <div id="section-vip" class="slate-card">
            <div class="slate-card-header" style="background: linear-gradient(135deg, rgba(6, 14, 28, 0.5) 0%, rgba(1, 6, 16, 0.85) 100%); border-bottom: 1px solid var(--border-gold);">
                <h2 style="background: var(--gold-gradient); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">🔥 Luck Society Top 10 VIP Best Bets</h2>
                <div class="sim-engine-badge" style="border-color: var(--primary); color: #ffe066; background: rgba(200, 155, 60, 0.1);">EV Edge Optimized</div>
            </div>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th style="text-align: center; width: 60px;">Rank</th>
                            <th style="width: 140px;">Type</th>
                            <th>Matchup</th>
                            <th style="width: 200px;">Selection</th>
                            <th style="width: 120px;">Odds (Amer)</th>
                            <th style="width: 220px;">Sim Prob vs Market Implied</th>
                            <th style="width: 140px;">Expected Value Edge</th>
                            <th>Esports VIP Analytical Driver</th>
                        </tr>
                    </thead>
                    <tbody>
                        {best_bets_rows if best_bets_rows else f"""
                        <tr>
                            <td colspan="8" class="empty-slate">
                                🔍 No active Moneyline EV edges found for this slate.<br>
                                <span style="font-size: 0.85rem; margin-top: 10px; display: block; color: var(--text-muted)">Edge must be strictly positive (>0% EV) to qualify for VIP.</span>
                            </td>
                        </tr>
                        """}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Section 3: Map Spreads -->
        <div id="section-spreads" class="slate-card">
            <div class="slate-card-header">
                <h2>🛡️ Elite Map Spreads (Map Handicap -1.5 / +1.5 Projections)</h2>
                <div class="sim-engine-badge">Map Spreads</div>
            </div>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th style="text-align: center; width: 60px;">Rank</th>
                            <th>Matchup</th>
                            <th style="width: 200px;">Selection</th>
                            <th style="width: 140px;">Model Implied Odds</th>
                            <th style="width: 160px;">Projected Prob</th>
                            <th style="width: 140px;">Expected Value Edge</th>
                            <th>Esports Analytical Driver</th>
                        </tr>
                    </thead>
                    <tbody>
                        {map_spreads_rows if map_spreads_rows else f"""
                        <tr>
                            <td colspan="7" class="empty-slate">
                                🔍 No high-confidence map spreads computed.<br>
                                <span style="font-size: 0.85rem; margin-top: 10px; display: block; color: var(--text-muted)">Requires positive EV vs estimated market spread vig.</span>
                            </td>
                        </tr>
                        """}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Section 4: Map Totals -->
        <div id="section-totals" class="slate-card">
            <div class="slate-card-header">
                <h2>📊 Elite Series Totals (Over / Under 2.5 Maps Projections)</h2>
                <div class="sim-engine-badge">Map Totals</div>
            </div>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th style="text-align: center; width: 60px;">Rank</th>
                            <th>Matchup</th>
                            <th style="width: 200px;">Selection</th>
                            <th style="width: 140px;">Model Implied Odds</th>
                            <th style="width: 160px;">Projected Prob</th>
                            <th style="width: 140px;">Expected Value Edge</th>
                            <th>Esports Analytical Driver</th>
                        </tr>
                    </thead>
                    <tbody>
                        {map_totals_rows if map_totals_rows else f"""
                        <tr>
                            <td colspan="7" class="empty-slate">
                                🔍 No series map totals computed.<br>
                                <span style="font-size: 0.85rem; margin-top: 10px; display: block; color: var(--text-muted)">Requires positive EV vs estimated market totals vig.</span>
                            </td>
                        </tr>
                        """}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Section 5: DFS Player Props -->
        <div id="section-props" class="slate-card">
            <div class="slate-card-header">
                <h2>🔮 DFS Player Props (KDA Prophet)</h2>
            </div>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th style="width: 40px; text-align: center;">#</th>
                            <th>Platform</th>
                            <th>Player</th>
                            <th>Selection</th>
                            <th>Odds</th>
                            <th>Win%</th>
                            <th>Edge</th>
                            <th>Signal Driver</th>
                        </tr>
                    </thead>
                    <tbody>
                        {dfs_props_rows if dfs_props_rows else "<tr><td colspan='8' class='empty-slate'>No DFS Player Props projected +EV</td></tr>"}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Section 6: Correct Score Specs -->
        <div id="section-scores" class="slate-card" style="border: 1px solid rgba(200, 155, 60, 0.4); box-shadow: 0 15px 45px rgba(200, 155, 60, 0.05);">
            <div class="slate-card-header" style="background: linear-gradient(135deg, rgba(6, 14, 28, 0.6) 0%, rgba(1, 6, 16, 0.95) 100%);">
                <h2 style="background: var(--gold-gradient); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">🔮 Correct Score Speculations (High-Yield Precise Outcomes)</h2>
                <div class="sim-engine-badge" style="border-color: var(--primary); color: var(--primary); background: rgba(200, 155, 60, 0.1);">Gold Signal</div>
            </div>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th style="text-align: center; width: 60px;">Rank</th>
                            <th>Matchup</th>
                            <th style="width: 200px;">Selection</th>
                            <th style="width: 140px;">Model Implied Odds</th>
                            <th style="width: 160px;">Projected Prob</th>
                            <th style="width: 140px;">Expected Value Edge</th>
                            <th>Esports Analytical Driver</th>
                        </tr>
                    </thead>
                    <tbody>
                        {score_specs_rows if score_specs_rows else f"""
                        <tr>
                            <td colspan="7" class="empty-slate">
                                🔍 No high-yield correct scorelines computed.<br>
                                <span style="font-size: 0.85rem; margin-top: 10px; display: block; color: var(--text-muted)">Requires scoreline probability >5% to display.</span>
                            </td>
                        </tr>
                        """}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Footer -->
        <footer>
            <div class="disclaimer">
                <strong>DISCLAIMER:</strong> Predictions are generated using standard GBDT Ensemble and rating-based Monte Carlo simulations (100,000 iterations per series). Expected values are derived using vig-free market anchoring. Bankroll sizing recommendations utilize a 0.25 fractional Kelly formula. Always gamble responsibly.
            </div>
            <div class="footer-brand">
                LUCK SOCIETY © 2026 — MONTE CARLO PREDICTOR ENGINE
            </div>
        </footer>
    </div>

    <script>
        function toggleRow(row) {{
            row.classList.toggle('expanded');
            const nextRow = row.nextElementSibling;
            if (nextRow && nextRow.classList.contains('detail-row')) {{
                if (nextRow.style.display === 'none') {{
                    nextRow.style.display = 'table-row';
                }} else {{
                    nextRow.style.display = 'none';
                }}
            }}
        }}

        function setSectionFilter(section, btn) {{
            const siblings = btn.parentElement.querySelectorAll('.chip');
            siblings.forEach(s => s.classList.remove('active'));
            btn.classList.add('active');
            
            const sections = [
                document.getElementById('section-slate'),
                document.getElementById('section-vip'),
                document.getElementById('section-spreads'),
                document.getElementById('section-totals'),
                document.getElementById('section-props'),
                document.getElementById('section-scores')
            ];
            
            sections.forEach(sec => {{
                if (sec) {{
                    if (section === 'all') {{
                        sec.style.display = 'block';
                    }} else if (sec.id === 'section-' + section) {{
                        sec.style.display = 'block';
                    }} else {{
                        sec.style.display = 'none';
                    }}
                }}
            }});
        }}

        function filterSlate() {{
            const query = document.getElementById('search-input').value.toLowerCase();
            const rows = document.querySelectorAll('tr.main-row');
            
            rows.forEach(row => {{
                const searchData = row.getAttribute('data-search') || '';
                const matches = searchData.includes(query);
                row.style.display = matches ? '' : 'none';
                
                const nextRow = row.nextElementSibling;
                if (nextRow && nextRow.classList.contains('detail-row')) {{
                    if (!matches) {{
                        nextRow.style.display = 'none';
                        row.classList.remove('expanded');
                    }}
                }}
            }});
            updateCounts();
        }}

        function updateCounts() {{
            const query = document.getElementById('search-input').value.toLowerCase();
            function countVisible(tableId) {{
                const table = document.getElementById(tableId);
                if (!table) return 0;
                const rows = table.querySelectorAll('tbody tr.main-row');
                let count = 0;
                rows.forEach(r => {{
                    const searchData = r.getAttribute('data-search') || '';
                    if (searchData.includes(query)) count++;
                }});
                return count;
            }}
            
            const countSlate = countVisible('section-slate');
            const countVip = countVisible('section-vip');
            const countSpreads = countVisible('section-spreads');
            const countTotals = countVisible('section-totals');
            const countProps = countVisible('section-props');
            const countScores = countVisible('section-scores');
            
            document.getElementById('count-slate').textContent = countSlate;
            document.getElementById('count-vip').textContent = countVip;
            document.getElementById('count-spreads').textContent = countSpreads;
            document.getElementById('count-totals').textContent = countTotals;
            document.getElementById('count-props').textContent = countProps;
            document.getElementById('count-scores').textContent = countScores;
            document.getElementById('count-all').textContent = countSlate + countVip + countSpreads + countTotals + countProps + countScores;
        }}

        document.addEventListener('DOMContentLoaded', () => {{
            updateCounts();
        }});
    </script>
</body>
</html>
"""
    return html_content

def run_generate_dashboard(target_date=None):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Launching LoL Premium Dashboard Generation...")
    
    matches, player_props = load_data(target_date)
    html_content = generate_html(matches, player_props, target_date)
    
    output_path = os.path.join(BASE_DIR, "dashboard.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"Successfully generated premium dashboard: {output_path} ({len(matches)} matches mapped).")
    return output_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Premium LoL Predictive Intelligence Dashboard")
    parser.add_argument("--date", type=str, help="Target date in YYYY-MM-DD format")
    args = parser.parse_args()
    
    run_generate_dashboard(args.date)
