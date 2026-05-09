#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════
LOL RECORD RESULTS — POST-MATCH OUTCOME RECORDER
═══════════════════════════════════════════════════════════════════════

Ported from MLB Omni-Prophet V16.0 record_results.py.
After matches complete, this tool:
  1. Finds all pending predictions for today (or a specified date)
  2. Prompts for winner and actual score
  3. Updates the prediction ledger with outcomes
  4. Updates JSON audit files
  5. Feeds data back into the calibration loop

Usage:
    python3 record_results.py              # Today's pending
    python3 record_results.py --date 2026-05-03
    python3 record_results.py --match-id "DRX_vs_NS_20260502"
"""

import sqlite3
import json
import os
import sys
import glob
import argparse
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LEDGER_DB = os.path.join(BASE_DIR, "data", "prediction_ledger.db")
AUDITS_DIR = os.path.join(BASE_DIR, "audits")


def get_pending_predictions(date_filter=None):
    """Get all pending predictions, optionally filtered by date."""
    if not os.path.exists(LEDGER_DB):
        print("  ❌ No prediction ledger found. Run some predictions first.")
        return []
    
    conn = sqlite3.connect(LEDGER_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if date_filter:
        cursor.execute("""
            SELECT match_id, league, team1, team2, model_prob, predicted_score, predicted_at
            FROM predictions WHERE winner IS NULL AND predicted_at LIKE ?
            ORDER BY predicted_at DESC
        """, (f"{date_filter}%",))
    else:
        cursor.execute("""
            SELECT match_id, league, team1, team2, model_prob, predicted_score, predicted_at
            FROM predictions WHERE winner IS NULL
            ORDER BY predicted_at DESC
        """)
    
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def record_outcome(match_id, winner, actual_score):
    """Record the outcome of a match."""
    conn = sqlite3.connect(LEDGER_DB)
    cursor = conn.cursor()
    
    # Get prediction
    cursor.execute("SELECT team1, team2, model_prob FROM predictions WHERE match_id = ?", (match_id,))
    row = cursor.fetchone()
    
    if not row:
        print(f"  ❌ No prediction found for: {match_id}")
        conn.close()
        return False
    
    team1, team2, model_prob = row
    
    # Determine correctness
    if model_prob > 0.5:
        predicted_winner = team1
    else:
        predicted_winner = team2
    
    correct = 1 if winner == predicted_winner else 0
    
    cursor.execute("""
        UPDATE predictions 
        SET winner = ?, actual_score = ?, outcome_recorded_at = ?, correct = ?
        WHERE match_id = ?
    """, (
        winner, actual_score,
        datetime.now(timezone.utc).isoformat(),
        correct, match_id
    ))
    conn.commit()
    conn.close()
    
    emoji = "✅" if correct else "❌"
    print(f"  {emoji} Recorded: {match_id}")
    print(f"     Winner: {winner} | Score: {actual_score}")
    print(f"     Predicted: {predicted_winner} ({model_prob*100:.1f}%) → {'CORRECT' if correct else 'WRONG'}")
    
    # Update audit file if it exists
    _update_audit(team1, team2, winner, actual_score, correct)
    
    return True


def _update_audit(team1, team2, winner, actual_score, correct):
    """Update the JSON audit file with outcome data."""
    if not os.path.exists(AUDITS_DIR):
        return
    
    # Search for matching audit files
    patterns = [
        os.path.join(AUDITS_DIR, f"audit_{team1}_{team2}_*.json"),
        os.path.join(AUDITS_DIR, f"audit_{team2}_{team1}_*.json"),
    ]
    
    for pattern in patterns:
        for filepath in glob.glob(pattern):
            try:
                with open(filepath, 'r') as f:
                    audit = json.load(f)
                
                audit['accuracy'] = {
                    'winner': winner,
                    'actual_score': actual_score,
                    'correct': correct,
                    'recorded_at': datetime.now(timezone.utc).isoformat(),
                }
                
                with open(filepath, 'w') as f:
                    json.dump(audit, f, indent=2, default=str)
                
                print(f"  📄 Updated audit: {os.path.basename(filepath)}")
            except Exception as e:
                print(f"  ⚠️  Failed to update audit {filepath}: {e}")


def interactive_mode(date_filter=None):
    """Interactive mode: show pending predictions and prompt for outcomes."""
    pending = get_pending_predictions(date_filter)
    
    if not pending:
        print(f"\n  ✅ No pending predictions{' for ' + date_filter if date_filter else ''}.")
        print("  All outcomes have been recorded.\n")
        return
    
    print(f"\n{'═'*72}")
    print(f"  📋 PENDING PREDICTIONS ({len(pending)})")
    print(f"{'═'*72}\n")
    
    for i, p in enumerate(pending):
        fav = p['team1'] if p['model_prob'] > 0.5 else p['team2']
        fav_prob = max(p['model_prob'], 1 - p['model_prob'])
        print(f"  [{i+1}] {p['team1']} vs {p['team2']} ({p['league']})")
        print(f"      Predicted: {fav} ({fav_prob*100:.1f}%) | Score: {p.get('predicted_score', '?')}")
        print(f"      ID: {p['match_id']}")
        print()
    
    print("  Enter outcomes below (or 'skip' / 'q' to quit):\n")
    
    for p in pending:
        print(f"  ── {p['team1']} vs {p['team2']} ──")
        
        winner = input(f"  Winner ({p['team1']}/{p['team2']}): ").strip()
        if winner.lower() in ('skip', 's'):
            continue
        if winner.lower() in ('quit', 'q'):
            break
        
        if winner not in (p['team1'], p['team2']):
            print(f"  ⚠️  '{winner}' not recognized. Skipping.")
            continue
        
        score = input(f"  Actual Score (e.g., 2-0, 2-1): ").strip()
        if not score:
            score = "N/A"
        
        record_outcome(p['match_id'], winner, score)
        print()
    
    print(f"\n{'═'*72}")
    print("  ✅ Done recording outcomes.")
    print("  Run calibration_check.py to see updated accuracy metrics.")
    print(f"{'═'*72}\n")


def main():
    parser = argparse.ArgumentParser(description="LoL Record Results — Post-Match Outcomes")
    parser.add_argument('--date', type=str, default=None,
                        help="Filter by date (YYYY-MM-DD)")
    parser.add_argument('--match-id', type=str, default=None,
                        help="Record a specific match by ID")
    parser.add_argument('--winner', type=str, default=None,
                        help="Winner team name (use with --match-id)")
    parser.add_argument('--score', type=str, default=None,
                        help="Actual score (use with --match-id)")
    
    args = parser.parse_args()
    
    if args.match_id:
        if not args.winner:
            print("  ❌ Must specify --winner with --match-id")
            sys.exit(1)
        record_outcome(args.match_id, args.winner, args.score or "N/A")
    else:
        interactive_mode(args.date)


if __name__ == '__main__':
    main()
