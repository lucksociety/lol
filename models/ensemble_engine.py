"""
═══════════════════════════════════════════════════════════════════════
ENSEMBLE CROSS-CHECK ENGINE — Quant-Elite 4.0
═══════════════════════════════════════════════════════════════════════

Runs two independent models and flags discrepancies:
  Model A: DeterministicLoL (roster power + synergy + context)
  Model B: PurePythonGBDT (statistical pattern matching)

If models disagree by >15%, the system warns before betting.
Final probability = weighted average (60% Deterministic, 40% GBDT).
"""

import os
import sys
import math

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from models.pure_python_ensemble import PurePythonGBDT


# Disagreement threshold
DISAGREEMENT_THRESHOLD = 0.15

# Model weights
DETERMINISTIC_WEIGHT = 0.60
GBDT_WEIGHT = 0.40


class EnsembleEngine:
    """
    Cross-check engine that combines DeterministicLoL and PurePythonGBDT
    to produce a more robust probability estimate.
    """

    def __init__(self):
        self.gbdt = PurePythonGBDT(n_estimators=15, learning_rate=0.1, max_depth=4)
        self._trained = False

    def _extract_features(self, team1, team2, det_model):
        """
        Extract feature vector for GBDT from match data.
        
        Features:
            0: team1 avg player power
            1: team2 avg player power
            2: power delta (t1 - t2)
            3: team1 synergy
            4: team2 synergy
            5: synergy ratio
            6: team1 max player power
            7: team2 max player power
            8: team1 elite count (players >= 93)
            9: team2 elite count (players >= 93)
            10: mid matchup delta
            11: adc matchup delta
        """
        t1_powers = [det_model._get_player_power(p) for p in team1.get("roster", [])]
        t2_powers = [det_model._get_player_power(p) for p in team2.get("roster", [])]

        t1_avg = sum(t1_powers) / max(len(t1_powers), 1)
        t2_avg = sum(t2_powers) / max(len(t2_powers), 1)

        t1_syn = det_model.team_synergy.get(team1.get("name", ""), 1.0)
        t2_syn = det_model.team_synergy.get(team2.get("name", ""), 1.0)

        t1_elites = sum(1 for p in t1_powers if p >= 93)
        t2_elites = sum(1 for p in t2_powers if p >= 93)

        # Lane matchups (index: 0=top, 1=jgl, 2=mid, 3=adc, 4=sup)
        mid_delta = (t1_powers[2] if len(t1_powers) > 2 else 80) - (t2_powers[2] if len(t2_powers) > 2 else 80)
        adc_delta = (t1_powers[3] if len(t1_powers) > 3 else 80) - (t2_powers[3] if len(t2_powers) > 3 else 80)

        return [
            t1_avg, t2_avg, t1_avg - t2_avg,
            t1_syn, t2_syn, t1_syn / max(t2_syn, 0.01),
            max(t1_powers) if t1_powers else 80,
            max(t2_powers) if t2_powers else 80,
            t1_elites, t2_elites,
            mid_delta, adc_delta
        ]

    def train_from_history(self, historical_matches, det_model):
        """
        Train the GBDT from historical match outcomes.
        
        Args:
            historical_matches: list of dicts with keys:
                team1, team2 (match dicts), winner (team1 or team2 name)
            det_model: DeterministicLoL instance for feature extraction
        """
        if not historical_matches:
            print("  ⚠️  No historical data for GBDT training.")
            return

        X = []
        y = []

        for match in historical_matches:
            features = self._extract_features(match["team1"], match["team2"], det_model)
            X.append(features)
            y.append(1.0 if match["winner"] == match["team1"].get("name") else 0.0)

        self.gbdt.fit(X, y)
        self._trained = True
        print(f"  ✅ GBDT trained on {len(X)} historical matches.")

    def predict(self, team1, team2, det_model, det_prob=None):
        """
        Run ensemble prediction with cross-check.
        
        Args:
            team1, team2: match team dicts
            det_model: DeterministicLoL instance
            det_prob: pre-computed deterministic probability (if available)
        
        Returns:
            dict with: final_prob, det_prob, gbdt_prob, disagreement, warning
        """
        # Model A: Deterministic
        if det_prob is None:
            det_prob = det_model.calculate_match_probability(team1, team2)

        # Model B: GBDT
        if self._trained:
            features = self._extract_features(team1, team2, det_model)
            gbdt_probs = self.gbdt.predict_proba([features])
            gbdt_prob = gbdt_probs[0][1]  # P(team1 wins)
        else:
            # If GBDT isn't trained, use deterministic only
            gbdt_prob = det_prob

        # Compute disagreement
        disagreement = abs(det_prob - gbdt_prob)
        warning = disagreement > DISAGREEMENT_THRESHOLD

        # Weighted average
        if self._trained:
            final_prob = (det_prob * DETERMINISTIC_WEIGHT) + (gbdt_prob * GBDT_WEIGHT)
        else:
            final_prob = det_prob

        final_prob = max(0.05, min(0.95, final_prob))

        result = {
            "final_prob": round(final_prob, 4),
            "det_prob": round(det_prob, 4),
            "gbdt_prob": round(gbdt_prob, 4),
            "disagreement": round(disagreement, 4),
            "warning": warning,
            "gbdt_trained": self._trained
        }

        if warning:
            t1_name = team1.get("name", "T1")
            t2_name = team2.get("name", "T2")
            print(f"\n  {'═'*60}")
            print(f"  ⚠️  MODEL DISAGREEMENT DETECTED")
            print(f"  {'═'*60}")
            print(f"  Match:        {t1_name} vs {t2_name}")
            print(f"  Deterministic: {det_prob*100:.1f}%")
            print(f"  GBDT:          {gbdt_prob*100:.1f}%")
            print(f"  Disagreement:  {disagreement*100:.1f}% (threshold: {DISAGREEMENT_THRESHOLD*100:.0f}%)")
            print(f"  → Recommend MANUAL REVIEW before betting.")
            print(f"  {'═'*60}\n")

        return result

    def print_crosscheck(self, result):
        """Pretty-print the ensemble cross-check results."""
        print(f"\n  ┌─ ENSEMBLE CROSS-CHECK ─────────────────────┐")
        print(f"  │  Deterministic:  {result['det_prob']*100:>5.1f}%                     │")
        
        if result["gbdt_trained"]:
            print(f"  │  GBDT:           {result['gbdt_prob']*100:>5.1f}%                     │")
            print(f"  │  Disagreement:   {result['disagreement']*100:>5.1f}%{'  ⚠️' if result['warning'] else '  ✅'}                  │")
            print(f"  │  Final (60/40):  {result['final_prob']*100:>5.1f}%                     │")
        else:
            print(f"  │  GBDT:           Not trained (using det only) │")
            print(f"  │  Final:          {result['final_prob']*100:>5.1f}%                     │")
        
        print(f"  └─────────────────────────────────────────────┘")
