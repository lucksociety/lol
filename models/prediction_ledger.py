"""
═══════════════════════════════════════════════════════════════════════
PREDICTION LEDGER — Quant-Elite 4.0
═══════════════════════════════════════════════════════════════════════

Tracks every prediction we make, records outcomes, and computes
calibration metrics so we know exactly how accurate the system is.

Usage:
    from models.prediction_ledger import PredictionLedger
    ledger = PredictionLedger()
    
    # After running a simulation:
    ledger.log_prediction(
        match_id="LCK_2026_W10_KT_BRO",
        league="LCK",
        team1="KT", team2="BRO",
        team1_roster=["PerfecT","Cuzz","Bdd","Aiming","Pollu"],
        team2_roster=["Casting","GIDEON","Loki","Teddy","Namgung"],
        model_prob=0.993,
        market_odds=None,
        predicted_score="2-0",
        notes="99.3% stomp probability"
    )
    
    # After the match:
    ledger.record_outcome("LCK_2026_W10_KT_BRO", winner="KT", actual_score="2-0")
    
    # Calibration report:
    ledger.generate_report()

CLI:
    python3 -m models.prediction_ledger report
    python3 -m models.prediction_ledger outcome LCK_2026_W10_KT_BRO KT 2-0
"""

import sqlite3
import os
import sys
import json
import argparse
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER_DB = os.path.join(BASE_DIR, "data", "prediction_ledger.db")


class PredictionLedger:
    """Persistent prediction tracking and calibration system."""

    def __init__(self, db_path=None):
        self.db_path = db_path or LEDGER_DB
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                match_id TEXT PRIMARY KEY,
                league TEXT,
                team1 TEXT,
                team2 TEXT,
                team1_roster TEXT,
                team2_roster TEXT,
                model_prob REAL,
                market_odds TEXT,
                predicted_score TEXT,
                notes TEXT,
                predicted_at TEXT,
                
                -- Outcome fields (filled in post-match)
                winner TEXT,
                actual_score TEXT,
                outcome_recorded_at TEXT,
                correct INTEGER
            )
        """)
        
        conn.commit()
        conn.close()

    def log_prediction(self, match_id, league, team1, team2,
                       team1_roster, team2_roster, model_prob,
                       market_odds=None, predicted_score=None, notes=None):
        """Log a prediction to the ledger."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO predictions 
                (match_id, league, team1, team2, team1_roster, team2_roster,
                 model_prob, market_odds, predicted_score, notes, predicted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                match_id, league, team1, team2,
                json.dumps(team1_roster), json.dumps(team2_roster),
                model_prob,
                json.dumps(market_odds) if market_odds else None,
                predicted_score, notes,
                datetime.now(timezone.utc).isoformat()
            ))
            conn.commit()
            print(f"  📝 Prediction logged: {match_id} ({team1} {model_prob*100:.1f}% vs {team2})")
        except Exception as e:
            print(f"  ⚠️  Failed to log prediction: {e}")
        finally:
            conn.close()

    def record_outcome(self, match_id, winner, actual_score):
        """Record the actual outcome of a match."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get the prediction to determine correctness
        cursor.execute("SELECT team1, model_prob FROM predictions WHERE match_id = ?", (match_id,))
        row = cursor.fetchone()
        
        if not row:
            print(f"  ❌ No prediction found for match_id: {match_id}")
            conn.close()
            return
        
        team1, model_prob = row
        # If model_prob > 0.5, we predicted team1. Check if team1 won.
        predicted_winner = team1 if model_prob > 0.5 else "team2"
        correct = 1 if (winner == team1 and model_prob > 0.5) or (winner != team1 and model_prob <= 0.5) else 0
        
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
        print(f"  {emoji} Outcome recorded: {match_id} → {winner} ({actual_score})")

    def generate_report(self):
        """Generate a full calibration report."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total predictions
        cursor.execute("SELECT COUNT(*) FROM predictions")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM predictions WHERE winner IS NOT NULL")
        resolved = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM predictions WHERE correct = 1")
        correct = cursor.fetchone()[0]
        
        print(f"\n{'═'*72}")
        print(f"  📊 QUANT-ELITE 4.0 — PREDICTION CALIBRATION REPORT")
        print(f"{'═'*72}")
        print(f"\n  Total Predictions:  {total}")
        print(f"  Resolved:           {resolved}")
        print(f"  Pending:            {total - resolved}")
        
        if resolved > 0:
            hit_rate = correct / resolved
            print(f"  Hit Rate:           {correct}/{resolved} ({hit_rate*100:.1f}%)")
            
            # Brier Score
            cursor.execute("""
                SELECT model_prob, team1, winner FROM predictions WHERE winner IS NOT NULL
            """)
            rows = cursor.fetchall()
            
            brier_sum = 0
            for prob, team1, winner in rows:
                actual = 1.0 if winner == team1 else 0.0
                brier_sum += (prob - actual) ** 2
            brier_score = brier_sum / resolved
            
            print(f"  Brier Score:        {brier_score:.4f} (lower is better, 0.25 = coin flip)")
            
            # Calibration by confidence bucket
            print(f"\n  {'─'*60}")
            print(f"  CALIBRATION BY CONFIDENCE BUCKET")
            print(f"  {'─'*60}")
            print(f"  {'Bucket':>15} {'Predicted':>12} {'Actual':>10} {'Count':>8} {'Status':>10}")
            print(f"  {'─'*60}")
            
            buckets = [
                (0.50, 0.60, "50-60%"),
                (0.60, 0.70, "60-70%"),
                (0.70, 0.80, "70-80%"),
                (0.80, 0.90, "80-90%"),
                (0.90, 1.01, "90-100%"),
            ]
            
            for lo, hi, label in buckets:
                bucket_rows = [r for r in rows if lo <= max(r[0], 1-r[0]) < hi]
                if not bucket_rows:
                    print(f"  {label:>15} {'—':>12} {'—':>10} {'0':>8} {'—':>10}")
                    continue
                    
                bucket_correct = sum(1 for r in bucket_rows 
                                     if (r[2] == r[1] and r[0] > 0.5) or 
                                        (r[2] != r[1] and r[0] <= 0.5))
                actual_rate = bucket_correct / len(bucket_rows)
                expected_rate = sum(max(r[0], 1-r[0]) for r in bucket_rows) / len(bucket_rows)
                
                delta = actual_rate - expected_rate
                if abs(delta) < 0.05:
                    status = "✅ GOOD"
                elif delta > 0:
                    status = "📈 OVER"
                else:
                    status = "📉 UNDER"
                
                print(f"  {label:>15} {expected_rate*100:>10.1f}% {actual_rate*100:>8.1f}% {len(bucket_rows):>8} {status:>10}")
            
            # By league
            print(f"\n  {'─'*60}")
            print(f"  PERFORMANCE BY LEAGUE")
            print(f"  {'─'*60}")
            
            cursor.execute("""
                SELECT league, COUNT(*), SUM(correct) 
                FROM predictions WHERE winner IS NOT NULL 
                GROUP BY league ORDER BY COUNT(*) DESC
            """)
            for league, count, wins in cursor.fetchall():
                rate = (wins or 0) / count
                print(f"  {league:>10}: {wins or 0}/{count} ({rate*100:.1f}%)")
        
        else:
            print(f"\n  ⚠️  No outcomes recorded yet. Use 'record_outcome()' after matches complete.")
        
        print(f"\n{'═'*72}\n")
        conn.close()

    def get_pending_predictions(self):
        """Get all predictions waiting for outcomes."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT match_id, team1, team2, model_prob, predicted_at 
            FROM predictions WHERE winner IS NULL
            ORDER BY predicted_at DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        return rows


def main():
    parser = argparse.ArgumentParser(description="Prediction Ledger — Quant-Elite 4.0")
    subparsers = parser.add_subparsers(dest="command")
    
    subparsers.add_parser("report", help="Generate calibration report")
    
    outcome_parser = subparsers.add_parser("outcome", help="Record a match outcome")
    outcome_parser.add_argument("match_id", help="Match ID")
    outcome_parser.add_argument("winner", help="Winning team code")
    outcome_parser.add_argument("score", help="Final score (e.g., 2-0, 2-1)")
    
    subparsers.add_parser("pending", help="Show predictions awaiting outcomes")
    
    args = parser.parse_args()
    ledger = PredictionLedger()
    
    if args.command == "report":
        ledger.generate_report()
    elif args.command == "outcome":
        ledger.record_outcome(args.match_id, args.winner, args.score)
    elif args.command == "pending":
        pending = ledger.get_pending_predictions()
        if not pending:
            print("\n  No pending predictions.\n")
        else:
            print(f"\n  📋 PENDING PREDICTIONS ({len(pending)})")
            for mid, t1, t2, prob, at in pending:
                print(f"    {mid}: {t1} ({prob*100:.1f}%) vs {t2} — logged {at[:10]}")
            print()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
