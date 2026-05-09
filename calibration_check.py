#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════
LOL CALIBRATION CHECK — PRE-SIMULATION FEEDBACK LOOP
═══════════════════════════════════════════════════════════════════════

Ported from MLB Omni-Prophet V16.0 architecture.
Reads prediction_ledger.db to detect systematic biases before running
new simulations. Produces CALIBRATION_MODIFIERS that are applied to
the prediction engine automatically.

Usage:
    python3 calibration_check.py              # Full report
    python3 calibration_check.py --league LCK # League-specific

Programmatic:
    from calibration_check import run_calibration_check
    modifiers = run_calibration_check()
    # modifiers = {
    #     'prob_adjustment': 0.97,   # Multiply final prob by this
    #     'league_adjustments': {'LCK': 1.02, 'LPL': 0.95},
    #     'upset_awareness': 0.03,   # Add to underdog prob
    #     'overall_accuracy': 0.65,
    #     'brier_score': 0.22,
    #     'n_resolved': 15,
    # }
"""

import sqlite3
import os
import sys
import argparse
import statistics
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LEDGER_DB = os.path.join(BASE_DIR, "data", "prediction_ledger.db")


def load_resolved_predictions(db_path=None, league=None):
    """Load all resolved predictions from the ledger."""
    if db_path is None:
        db_path = LEDGER_DB
    if not os.path.exists(db_path):
        return []
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = """
        SELECT match_id, league, team1, team2, model_prob, 
               predicted_score, winner, actual_score, correct,
               predicted_at, outcome_recorded_at
        FROM predictions 
        WHERE winner IS NOT NULL
    """
    params = []
    if league:
        query += " AND league = ?"
        params.append(league)
    query += " ORDER BY predicted_at ASC"
    
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def load_pending_predictions(db_path=None):
    """Load all pending (unresolved) predictions."""
    if db_path is None:
        db_path = LEDGER_DB
    if not os.path.exists(db_path):
        return []
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT match_id, league, team1, team2, model_prob, predicted_at
        FROM predictions WHERE winner IS NULL
        ORDER BY predicted_at DESC
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def analyze_probability_calibration(predictions, n_recent=None):
    """Analyze calibration by confidence bucket.
    
    Answers: When we say 70%, does team1 actually win ~70% of the time?
    """
    if n_recent:
        predictions = predictions[-n_recent:]
    if not predictions:
        return {'status': 'INSUFFICIENT_DATA', 'n': 0}
    
    buckets = [
        (0.50, 0.60, "50-60%"),
        (0.60, 0.70, "60-70%"),
        (0.70, 0.80, "70-80%"),
        (0.80, 0.90, "80-90%"),
        (0.90, 1.01, "90-100%"),
    ]
    
    bucket_results = []
    total_overconfident = 0
    total_underconfident = 0
    
    for lo, hi, label in buckets:
        # Get predictions where the favored team's probability falls in this bucket
        bucket_preds = []
        for p in predictions:
            fav_prob = max(p['model_prob'], 1 - p['model_prob'])
            if lo <= fav_prob < hi:
                bucket_preds.append(p)
        
        if not bucket_preds:
            bucket_results.append({
                'label': label, 'expected': 0, 'actual': 0,
                'count': 0, 'delta': 0, 'status': '—'
            })
            continue
        
        # Expected win rate = average of favored probabilities
        expected_rate = sum(max(p['model_prob'], 1 - p['model_prob']) for p in bucket_preds) / len(bucket_preds)
        
        # Actual win rate = how often the favored team won
        correct = sum(1 for p in bucket_preds if p.get('correct', 0) == 1)
        actual_rate = correct / len(bucket_preds)
        
        delta = actual_rate - expected_rate
        if abs(delta) < 0.05:
            status = "✅ CALIBRATED"
        elif delta > 0:
            status = "📈 UNDER-CONF"  # We were too cautious
            total_underconfident += len(bucket_preds)
        else:
            status = "📉 OVER-CONF"   # We were too aggressive
            total_overconfident += len(bucket_preds)
        
        bucket_results.append({
            'label': label, 'expected': expected_rate, 'actual': actual_rate,
            'count': len(bucket_preds), 'delta': delta, 'status': status
        })
    
    # Compute overall probability adjustment
    total_with_data = sum(b['count'] for b in bucket_results if b['count'] > 0)
    prob_adjustment = 1.0
    if total_with_data >= 5:
        # Weighted average of bucket deltas
        weighted_delta = sum(b['delta'] * b['count'] for b in bucket_results if b['count'] > 0)
        weighted_delta /= total_with_data
        
        if weighted_delta < -0.05:
            # We're overconfident — dampen probabilities
            prob_adjustment = 1.0 + weighted_delta  # e.g., 0.93 if delta = -0.07
            prob_adjustment = max(0.85, prob_adjustment)
        elif weighted_delta > 0.05:
            # We're underconfident — boost probabilities
            prob_adjustment = 1.0 + (weighted_delta * 0.5)  # More conservative boost
            prob_adjustment = min(1.10, prob_adjustment)
    
    return {
        'buckets': bucket_results,
        'prob_adjustment': round(prob_adjustment, 3),
        'n': len(predictions),
        'overconfident_count': total_overconfident,
        'underconfident_count': total_underconfident,
    }


def analyze_directional_accuracy(predictions, n_recent=None):
    """Analyze how often we pick the right winner."""
    if n_recent:
        predictions = predictions[-n_recent:]
    if not predictions:
        return {'accuracy': 0, 'n': 0}
    
    correct = sum(1 for p in predictions if p.get('correct', 0) == 1)
    
    return {
        'accuracy': correct / len(predictions) * 100,
        'correct': correct,
        'total': len(predictions),
        'n': len(predictions),
    }


def analyze_upset_rate(predictions, n_recent=None):
    """Analyze how often heavy favorites (>80%) lose.
    
    If upsets happen more than expected, we need to boost underdog probabilities.
    """
    if n_recent:
        predictions = predictions[-n_recent:]
    if not predictions:
        return {'upset_awareness': 0.0, 'n': 0}
    
    heavy_fav_preds = []
    for p in predictions:
        fav_prob = max(p['model_prob'], 1 - p['model_prob'])
        if fav_prob >= 0.75:
            heavy_fav_preds.append(p)
    
    if len(heavy_fav_preds) < 3:
        return {'upset_awareness': 0.0, 'n': len(heavy_fav_preds), 'status': 'INSUFFICIENT_DATA'}
    
    upsets = sum(1 for p in heavy_fav_preds if p.get('correct', 0) == 0)
    upset_rate = upsets / len(heavy_fav_preds)
    
    # Expected upset rate for 75%+ favorites: ~20-25%
    expected_upset_rate = 1.0 - sum(max(p['model_prob'], 1 - p['model_prob']) for p in heavy_fav_preds) / len(heavy_fav_preds)
    
    upset_excess = upset_rate - expected_upset_rate
    
    # If upsets happen more than expected, add a modifier to underdog probabilities
    upset_awareness = 0.0
    if upset_excess > 0.05:
        upset_awareness = min(0.05, upset_excess * 0.5)
    
    return {
        'upset_awareness': round(upset_awareness, 3),
        'upset_rate': round(upset_rate, 3),
        'expected_upset_rate': round(expected_upset_rate, 3),
        'upset_excess': round(upset_excess, 3),
        'n': len(heavy_fav_preds),
        'upsets': upsets,
    }


def analyze_league_bias(predictions):
    """Analyze per-league accuracy to find systematic biases."""
    leagues = {}
    for p in predictions:
        league = p.get('league', 'Unknown')
        if league not in leagues:
            leagues[league] = {'correct': 0, 'total': 0, 'probs': [], 'actuals': []}
        leagues[league]['total'] += 1
        if p.get('correct', 0) == 1:
            leagues[league]['correct'] += 1
        leagues[league]['probs'].append(max(p['model_prob'], 1 - p['model_prob']))
        leagues[league]['actuals'].append(1 if p.get('correct', 0) == 1 else 0)
    
    league_adjustments = {}
    for league, data in leagues.items():
        if data['total'] < 3:
            continue
        accuracy = data['correct'] / data['total']
        avg_prob = sum(data['probs']) / data['total']
        
        # If accuracy is significantly below our average confidence, apply dampener
        delta = accuracy - avg_prob
        if abs(delta) > 0.05:
            adjustment = 1.0 + (delta * 0.3)  # 30% of the delta as correction
            adjustment = max(0.85, min(1.15, adjustment))
        else:
            adjustment = 1.0
        
        league_adjustments[league] = {
            'adjustment': round(adjustment, 3),
            'accuracy': round(accuracy * 100, 1),
            'avg_confidence': round(avg_prob * 100, 1),
            'record': f"{data['correct']}/{data['total']}",
        }
    
    return league_adjustments


def compute_brier_score(predictions):
    """Compute Brier Score — lower is better, 0.25 = coin flip."""
    if not predictions:
        return None
    
    brier_sum = 0
    for p in predictions:
        actual = 1.0 if p.get('correct', 0) == 1 else 0.0
        # Use the probability of the favored team
        fav_prob = max(p['model_prob'], 1 - p['model_prob'])
        brier_sum += (fav_prob - actual) ** 2
    
    return round(brier_sum / len(predictions), 4)


def analyze_score_prediction_accuracy(predictions, n_recent=None):
    """Analyze how often we predict the correct series score (2-0, 2-1, etc.)."""
    if n_recent:
        predictions = predictions[-n_recent:]
    
    with_scores = [p for p in predictions 
                   if p.get('predicted_score') and p.get('actual_score')]
    
    if not with_scores:
        return {'exact_score_rate': 0, 'n': 0}
    
    exact_matches = sum(1 for p in with_scores 
                        if p['predicted_score'] == p['actual_score'])
    
    return {
        'exact_score_rate': round(exact_matches / len(with_scores) * 100, 1),
        'exact_matches': exact_matches,
        'n': len(with_scores),
    }


def run_calibration_check(db_path=None, league=None):
    """Execute the full calibration check and return modifiers.
    
    Returns:
        dict with calibration modifiers to apply to next simulation.
    """
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║       LOL OMNI-PROPHET V5.0 | CALIBRATION CHECK               ║")
    print("╚══════════════════════════════════════════════════════════════════╝\n")
    
    predictions = load_resolved_predictions(db_path, league)
    pending = load_pending_predictions(db_path)
    
    print(f"  Total Resolved: {len(predictions)} | Pending: {len(pending)}")
    
    if not predictions:
        print("\n  [INSUFFICIENT DATA — No resolved predictions in ledger]")
        print("  → Running with NEUTRAL modifiers (no correction applied)")
        print(f"\n{'='*66}")
        return {
            'prob_adjustment': 1.0,
            'league_adjustments': {},
            'upset_awareness': 0.0,
            'overall_accuracy': 0,
            'brier_score': None,
            'n_resolved': 0,
            'status': 'COLD_START',
        }
    
    # 1. Probability Calibration
    cal = analyze_probability_calibration(predictions)
    print(f"\n── 1. PROBABILITY CALIBRATION (n={cal['n']}) ────────────────────────")
    if cal.get('buckets'):
        print(f"  {'Bucket':>15} {'Expected':>10} {'Actual':>10} {'Count':>8} {'Status':>15}")
        print(f"  {'─'*60}")
        for b in cal['buckets']:
            if b['count'] > 0:
                print(f"  {b['label']:>15} {b['expected']*100:>8.1f}% {b['actual']*100:>8.1f}% {b['count']:>8} {b['status']:>15}")
            else:
                print(f"  {b['label']:>15} {'—':>10} {'—':>10} {'0':>8} {'—':>15}")
    print(f"  → PROBABILITY MODIFIER: {cal['prob_adjustment']:.3f}x")
    
    # 2. Directional Accuracy
    dir_acc = analyze_directional_accuracy(predictions)
    print(f"\n── 2. DIRECTIONAL ACCURACY ──────────────────────────────────────")
    print(f"  Winner Correct: {dir_acc['correct']}/{dir_acc['total']} ({dir_acc['accuracy']:.1f}%)")
    
    # 3. Upset Analysis
    upset = analyze_upset_rate(predictions)
    print(f"\n── 3. UPSET AWARENESS ANALYSIS ──────────────────────────────────")
    if upset['n'] >= 3:
        print(f"  Heavy Favorites (>75%): {upset['n']} predictions")
        print(f"  Upset Rate: {upset['upset_rate']*100:.1f}% (expected: {upset['expected_upset_rate']*100:.1f}%)")
        print(f"  → UPSET AWARENESS MODIFIER: +{upset['upset_awareness']*100:.1f}% to underdogs")
    else:
        print(f"  [INSUFFICIENT DATA — need 3+ heavy-favorite predictions]")
    
    # 4. League-Specific Bias
    league_adj = analyze_league_bias(predictions)
    print(f"\n── 4. LEAGUE-SPECIFIC BIAS ──────────────────────────────────────")
    if league_adj:
        for lg, data in sorted(league_adj.items()):
            print(f"  {lg:>10}: {data['record']} ({data['accuracy']:.1f}%) | Avg Conf: {data['avg_confidence']:.1f}% | Adj: {data['adjustment']:.3f}x")
    else:
        print("  [INSUFFICIENT DATA]")
    
    # 5. Brier Score
    brier = compute_brier_score(predictions)
    print(f"\n── 5. BRIER SCORE ──────────────────────────────────────────────")
    if brier is not None:
        quality = "EXCELLENT" if brier < 0.15 else "GOOD" if brier < 0.20 else "FAIR" if brier < 0.25 else "POOR (worse than coin flip)"
        print(f"  Brier Score: {brier:.4f} ({quality})")
        print(f"  (0.00 = perfect, 0.25 = coin flip)")
    
    # 6. Score Prediction Accuracy
    score_acc = analyze_score_prediction_accuracy(predictions)
    print(f"\n── 6. EXACT SCORE PREDICTION ────────────────────────────────────")
    if score_acc['n'] > 0:
        print(f"  Exact Score Hit Rate: {score_acc['exact_matches']}/{score_acc['n']} ({score_acc['exact_score_rate']:.1f}%)")
    else:
        print("  [NO SCORE DATA]")
    
    print(f"\n{'='*66}")
    
    # Compile modifiers
    modifiers = {
        'prob_adjustment': cal.get('prob_adjustment', 1.0),
        'league_adjustments': {k: v['adjustment'] for k, v in league_adj.items()},
        'upset_awareness': upset.get('upset_awareness', 0.0),
        'overall_accuracy': dir_acc.get('accuracy', 0),
        'brier_score': brier,
        'n_resolved': len(predictions),
        'status': 'ACTIVE',
    }
    
    print(f"\n  ACTIVE MODIFIERS FOR NEXT SIMULATION:")
    print(f"    Prob Adjustment:   {modifiers['prob_adjustment']:.3f}x")
    print(f"    Upset Awareness:   +{modifiers['upset_awareness']*100:.1f}%")
    if modifiers['league_adjustments']:
        for lg, adj in modifiers['league_adjustments'].items():
            print(f"    {lg} Adj:          {adj:.3f}x")
    
    return modifiers


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="LoL Calibration Check — Omni-Prophet V5.0")
    parser.add_argument('--league', type=str, default=None, help="Filter by league (LCK, LPL, LEC)")
    args = parser.parse_args()
    
    run_calibration_check(league=args.league)
