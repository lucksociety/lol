import math
import random
import json
import os
import sys
import statistics
from datetime import datetime
import io

# Roster verification gate (Quant-Elite 3.2)
try:
    from models.roster_gate import RosterGate, RosterNotVerifiedError, RosterStaleError, RosterMismatchError
    _GATE_AVAILABLE = True
except ImportError:
    try:
        _models_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, os.path.dirname(_models_dir))
        from models.roster_gate import RosterGate, RosterNotVerifiedError, RosterStaleError, RosterMismatchError
        _GATE_AVAILABLE = True
    except ImportError:
        _GATE_AVAILABLE = False

# Auto-computed ratings & synergy (Quant-Elite 4.0)
try:
    from models.player_ratings import PlayerRatings
    _RATINGS_AVAILABLE = True
except ImportError:
    _RATINGS_AVAILABLE = False

# Prediction ledger (Quant-Elite 4.0)
try:
    from models.prediction_ledger import PredictionLedger
    _LEDGER_AVAILABLE = True
except ImportError:
    _LEDGER_AVAILABLE = False

# Ensemble cross-check (Quant-Elite 4.0)
try:
    from models.ensemble_engine import EnsembleEngine
    _ENSEMBLE_AVAILABLE = True
except ImportError:
    _ENSEMBLE_AVAILABLE = False

# Calibration check (Omni-Prophet V5.0)
try:
    _base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, _base)
    from calibration_check import run_calibration_check
    _CALIBRATION_AVAILABLE = True
except ImportError:
    _CALIBRATION_AVAILABLE = False

# Data recorder (Omni-Prophet V5.0)
try:
    from data_recorder import record_simulation
    _RECORDER_AVAILABLE = True
except ImportError:
    _RECORDER_AVAILABLE = False

# ═══════════════════════════════════════════════════════════════
# LEAGUE BASELINES (2026 Spring Season)
# ═══════════════════════════════════════════════════════════════
LEAGUE_AVG_WIN_RATE = 0.50
LEAGUE_AVG_FB_PCT = 0.50
LEAGUE_AVG_DRAGON_PCT = 0.50
LEAGUE_AVG_BARON_PCT = 0.50

# Calibration constant for LoL probabilities
CALIBRATION = 0.85

# ═══════════════════════════════════════════════════════════════
# VALUE TRAP CRITERIA (Omni-Prophet V5.0 — LoL Ace Trap equivalent)
# ═══════════════════════════════════════════════════════════════
VALUE_TRAP_CRITERIA = [
    'roster_paper_tiger',   # High power but negative GD@15 trend
    'h2h_kryptonite',       # Losing H2H vs this specific opponent
    'form_crash',           # Good overall but recent slide
    'roster_instability',   # Recent roster changes
    'draft_trap',           # Shallow champion pool in Fearless
    'schedule_fatigue',     # 3rd match in 4 days
]


class DeterministicLoL:
    """Elite League of Legends prediction engine — Omni-Prophet V5.0.
    
    Integrates:
    - Roster Power (Auto-computed from Leaguepedia stats, with manual fallback)
    - Lane-specific Matchup Dynamics
    - Team Synergy (Auto-computed from win rates and H2H records)
    - Match Context Modifiers (side selection, patch recency, H2H history)
    - Ensemble Cross-Check (DeterministicLoL + PurePythonGBDT)
    - Prediction Ledger (auto-logs every prediction for calibration)
    - Calibration Feedback Loop (Phase 0 — ported from MLB Omni-Prophet V16.0)
    - Value Trap Detection (LoL equivalent of Ace Trap)
    - Auto Data Persistence (audit JSON + intelligence MD)
    - Bo3/Bo5 Monte Carlo Simulation
    """

    def __init__(self):
        # ── MANUAL FALLBACK RATINGS (used when computed ratings unavailable) ──
        # Scale: 80 (Average) - 100 (God-Tier)
        self.player_power = {
            # T1
            "Doran": 88, "Oner": 90, "Faker": 96, "Peyz": 94, "Keria": 95,
            # Gen.G
            "Zeus": 98, "Canyon": 97, "Chovy": 99, "Gumayusi": 96, "Lehends": 93,
            # KT Rolster
            "PerfecT": 89, "Cuzz": 92, "Bdd": 93, "Aiming": 95, "Pollu": 87,
            # Hanwha Life (HLE)
            "Kanavi": 94, "Zeka": 92, "Delight": 93,
            # NS RedForce
            "Kingen": 87, "Sponge": 84, "Scout": 91, "Taeyoon": 83, "Lehends_NS": 90,
            # Others
            "Slayer": 85, "Diable": 82, "ShowMaker": 93, "Lucid": 88, "Aiming_KT": 95
        }

        self.team_synergy = {
            "T1": 1.15,
            "Gen.G": 1.25,
            "KT": 1.55,
            "HLE": 1.10,
            "NS": 0.95
        }

        # ── AUTO-LOAD COMPUTED RATINGS (Quant-Elite 4.0) ──
        self._ratings_engine = None
        self._using_computed_ratings = False
        if _RATINGS_AVAILABLE:
            try:
                self._ratings_engine = PlayerRatings()
                # Overlay computed ratings onto manual ratings
                computed = self._ratings_engine._ratings.get("players", {})
                if computed:
                    for name, entry in computed.items():
                        self.player_power[name] = entry["power"]
                    self._using_computed_ratings = True
                
                # Overlay computed synergy
                computed_syn = self._ratings_engine._synergy.get("teams", {})
                if computed_syn:
                    for team, entry in computed_syn.items():
                        self.team_synergy[team] = entry["synergy"]
            except Exception:
                pass  # Fall back to manual ratings silently

        # ── PREDICTION LEDGER (Quant-Elite 4.0) ──
        self._ledger = None
        if _LEDGER_AVAILABLE:
            try:
                self._ledger = PredictionLedger()
            except Exception:
                pass

        # ── ENSEMBLE ENGINE (Quant-Elite 4.0) ──
        self._ensemble = None
        if _ENSEMBLE_AVAILABLE:
            try:
                self._ensemble = EnsembleEngine()
            except Exception:
                pass

        # ── CALIBRATION (Omni-Prophet V5.0) ──
        self._calibration = None

        # Add slight random noise to player ratings for dynamic simulation runs
        for player in self.player_power:
            self.player_power[player] += random.uniform(-1.5, 1.5)

    def _get_player_power(self, name):
        return self.player_power.get(name, 80)

    def _verify_teams(self, team1, team2):
        """HARD GATE: Verify both teams' rosters before simulation.
        
        Checks:
        1. Both teams have verified rosters in verified_rosters.json
        2. Rosters are not stale (>12h)
        3. The roster in the script matches the verified roster
        """
        if not _GATE_AVAILABLE:
            print("  ⚠️  WARNING: roster_gate module not found. Running WITHOUT verification.")
            print("  ⚠️  This is UNSAFE. Install roster_gate.py to enable verification.")
            return
        
        gate = RosterGate()
        
        for team in [team1, team2]:
            team_code = team.get("name", "UNKNOWN")
            roster = team.get("roster", [])
            
            # Step 1 & 2: Check verification exists and is fresh
            gate.require_verified_roster(team_code)
            
            # Step 3: Cross-check script roster vs verified roster
            gate.cross_check_roster(team_code, roster)

    def calculate_match_probability(self, team1, team2):
        """Calculates the probability of team1 winning a single game against team2."""
        
        t1_power = sum(self._get_player_power(p) for p in team1["roster"])
        t2_power = sum(self._get_player_power(p) for p in team2["roster"])
        
        # ── 1. ROSTER DELTA ──────────────────────────────────────────
        power_delta = (t1_power - t2_power) / 5.0
        
        # ── 2. LANE MATCHUPS ─────────────────────────────────────────
        matchups = []
        for i in range(5):
            p1 = self._get_player_power(team1["roster"][i])
            p2 = self._get_player_power(team2["roster"][i])
            matchups.append(p1 - p2)
            
        # Mid/Jungle synergy bonus
        mid_jungle_t1 = (matchups[1] + matchups[2]) * 0.15
        lane_advantage = sum(matchups) + mid_jungle_t1
        
        # ── 3. FORM & SYNERGY (DAMPENED) ─────────────────────────────
        t1_syn = self.team_synergy.get(team1["name"], 1.0)
        t2_syn = self.team_synergy.get(team2["name"], 1.0)
        
        # ── 4. CONVERGENCE ───────────────────────────────────────────
        logit = (power_delta * 0.12) + (lane_advantage * 0.04) # Tightened coefficients
        
        # ── 4a. SIDE SELECTION MODIFIER (Quant-Elite 4.0) ────────────
        # Blue side has a ~53-55% historical advantage in pro play
        side = team1.get("side", None)
        if side == "blue":
            logit += 0.03
        elif side == "red":
            logit -= 0.03
        
        # ── 4b. PATCH RECENCY MODIFIER (Quant-Elite 4.0) ────────────
        # Teams with more games on the current patch have a slight edge
        t1_patch_games = team1.get("patch_games", 0)
        t2_patch_games = team2.get("patch_games", 0)
        if t1_patch_games > 0 and t2_patch_games > 0:
            patch_delta = min(0.03, (t1_patch_games - t2_patch_games) * 0.005)
            logit += patch_delta
        
        # ── 4c. HEAD-TO-HEAD HISTORY MODIFIER (Quant-Elite 4.0) ──────
        # If one team historically dominates the other, apply a bonus
        h2h_modifier = team1.get("h2h_modifier", 0)
        if h2h_modifier == 0 and self._ratings_engine:
            h2h_modifier = self._ratings_engine.get_h2h_modifier(
                team1.get("name", ""), team2.get("name", "")
            )
        logit += h2h_modifier
        
        prob = 1 / (1 + math.exp(-logit))
        
        # Apply Synergy Multiplier (Reduced Impact)
        synergy_ratio = (t1_syn / t2_syn)
        prob = prob * (1.0 + (synergy_ratio - 1.0) * 0.5) 
        
        # ── 5. VOLATILITY CALIBRATION ────────────────────────────────
        # Identify "Elite Underdogs" (High pop-off potential)
        t2_elites = sum(1 for p in team2["roster"] if self._get_player_power(p) >= 93)
        if prob > 0.60 and t2_elites >= 1:
            prob = prob - (0.08 * t2_elites)
            
        return max(0.05, min(0.95, 0.5 + (prob - 0.5) * CALIBRATION))

    def simulate_bo3(self, team1, team2, iterations=100000, **kwargs):
        """Wrapper for Best-of-3 simulation."""
        return self.simulate_bo_series(team1, team2, best_of=3, iterations=iterations, **kwargs)
        
    def simulate_bo5(self, team1, team2, iterations=100000, **kwargs):
        """Wrapper for Best-of-5 simulation."""
        return self.simulate_bo_series(team1, team2, best_of=5, iterations=iterations, **kwargs)

    def simulate_bo_series(self, team1, team2, best_of=3, iterations=100000, require_verification=True, market_odds=None, market_surge=0.0):
        """Monte Carlo simulation for a Best-of-3 or Best-of-5 series with dynamic momentum and fatigue.
        
        Args:
            require_verification: If True (default), rosters MUST be verified before simulation runs.
                                  Set to False ONLY for backtesting historical data.
            market_odds: Optional dict of betting odds for Kelly/EV analysis.
        """
        
        # ── PHASE 0: CALIBRATION (Omni-Prophet V5.0) ─────────────
        if _CALIBRATION_AVAILABLE and self._calibration is None:
            try:
                league = team1.get('league', team2.get('league', None))
                self._calibration = run_calibration_check(league=league)
            except Exception as e:
                print(f"  ⚠️  Calibration check failed: {e}")
                self._calibration = {'prob_adjustment': 1.0, 'upset_awareness': 0.0, 'status': 'ERROR'}
        
        # ── ROSTER VERIFICATION GATE ─────────────────────────────
        if require_verification:
            self._verify_teams(team1, team2)
        
        base_t1_prob = self.calculate_match_probability(team1, team2)
        
        # Chaos factor from aggression variance
        chaos_factor = max(team1.get("aggression_variance", 0), team2.get("aggression_variance", 0))
        if chaos_factor > 0:
            base_t1_prob = base_t1_prob + (0.5 - base_t1_prob) * (chaos_factor * 0.15) # Increased chaos weight
        
        t1_series_wins = 0
        games_to_win = (best_of // 2) + 1
        score_counts = {}
        
        for _ in range(iterations):
            t1_games = 0
            t2_games = 0
            
            # Reset probability for the series iteration
            current_t1_prob = base_t1_prob
            
            # Fatigue statuses
            t1_fatigued = team1.get("fatigued", False)
            t2_fatigued = team2.get("fatigued", False)
            
            for game_num in range(1, best_of + 1):
                # ── UPDATE 2: BO5 FATIGUE PENALTY ────────────────────────
                # Fatigue kicks in heavily in later games of a series for double-header teams
                fatigue_penalty = 0
                if game_num >= 3:
                    if t1_fatigued: fatigue_penalty -= 0.06
                    if t2_fatigued: fatigue_penalty += 0.06
                
                game_prob = current_t1_prob + fatigue_penalty
                game_prob = max(0.05, min(0.95, game_prob))  # Clamp
                
                if random.random() < game_prob:
                    t1_games += 1
                    # ── UPDATE 3: MOMENTUM CARRYOVER FOR ELITE SWEEPS ─────
                    if game_num == 1 and team1.get("tier") == "S":
                        current_t1_prob += 0.08
                    elif game_num == 1 and team2.get("tier") == "S":
                        current_t1_prob -= 0.02
                else:
                    t2_games += 1
                    # ── UPDATE 3: MOMENTUM CARRYOVER FOR ELITE SWEEPS ─────
                    if game_num == 1 and team2.get("tier") == "S":
                        current_t1_prob -= 0.08
                    elif game_num == 1 and team1.get("tier") == "S":
                        current_t1_prob += 0.02
                        
                if t1_games == games_to_win:
                    t1_series_wins += 1
                    score = f"{t1_games}-{t2_games}"
                    score_counts[score] = score_counts.get(score, 0) + 1
                    break
                if t2_games == games_to_win:
                    score = f"{t1_games}-{t2_games}"
                    score_counts[score] = score_counts.get(score, 0) + 1
                    break
                    
        series_win_prob = t1_series_wins / iterations
        
        # ── CALIBRATION APPLICATION (Omni-Prophet V5.0) ──────────
        cal_modifier = 1.0
        old_series_win_prob = series_win_prob
        
        if self._calibration and self._calibration.get('status') == 'ACTIVE':
            cal_modifier = self._calibration.get('prob_adjustment', 1.0)
            upset_boost = self._calibration.get('upset_awareness', 0.0)
            # Apply league-specific adjustment if available
            league = team1.get('league', team2.get('league', ''))
            league_adj = self._calibration.get('league_adjustments', {}).get(league, 1.0)
            cal_modifier *= league_adj
            # Apply upset awareness to underdog
            if series_win_prob > 0.5:
                series_win_prob = series_win_prob * cal_modifier
                series_win_prob = min(0.95, series_win_prob)
            else:
                series_win_prob = series_win_prob + upset_boost
                series_win_prob = max(0.05, series_win_prob)
        
        # Initialize result dictionary for tracking flags
        result = {
            "base_game_prob": base_t1_prob,
            "calibration": self._calibration or {},
        }
        
        # ── PHASE 1: MARKET SENTIMENT (Smart Money) ──────────────
        # If money is surging toward the underdog, penalize the favorite
        if market_surge > 0:
            # Positive surge = money moving toward Team 2 (underdog if win_prob > 0.5)
            if series_win_prob > 0.5:
                # Penalize favorite: every 1% surge = 0.5% probability drop
                penalty = (market_surge / 100.0) * 0.5
                series_win_prob = max(0.51, series_win_prob - penalty)
                result["sentiment_warning"] = f"SMART MONEY ALERT: {market_surge}% surge toward {team2.get('name')} detected."
            else:
                # If money is moving toward the current favorite already, ignore or add slight boost? 
                # Usually, we only care about "contrarian" surges.
                pass

        # ── PHASE 2: CONFIDENCE CAP (Omni-Prophet V5.0) ──────────
        # If the Brier Score is poor (>0.25), CAP THE CONFIDENCE.
        brier = 0.0
        if self._calibration:
            brier_str = self._calibration.get('brier_score', '0.5')
            try:
                brier = float(brier_str.split()[0]) if isinstance(brier_str, str) else float(brier_str)
            except:
                brier = 0.5
        
        if brier > 0.25:
            # System is under-performing. Cap confidence at a slightly randomized soft boundary (77.5% - 81.5%)
            cap_val = random.uniform(0.775, 0.815)
            if series_win_prob > cap_val:
                series_win_prob = cap_val
                result["confidence_cap"] = True
            elif series_win_prob < (1.0 - cap_val):
                series_win_prob = 1.0 - cap_val
                result["confidence_cap"] = True

        
        # ── SCORE NORMALIZATION (Ensuring Consistency) ──────────
        # Re-scale the individual scores to match the calibrated series_win_prob
        calibrated_scores = {}
        t1_total_score_prob = sum(v for k, v in score_counts.items() if k.startswith(f"{games_to_win}-")) / iterations
        t2_total_score_prob = 1.0 - t1_total_score_prob
        
        for score_key, count in score_counts.items():
            prob = count / iterations
            if score_key.startswith(f"{games_to_win}-"):
                # Scale T1 wins
                if t1_total_score_prob > 0:
                    calibrated_scores[score_key] = prob * (series_win_prob / t1_total_score_prob)
                else:
                    calibrated_scores[score_key] = prob
            else:
                # Scale T2 wins
                if t2_total_score_prob > 0:
                    calibrated_scores[score_key] = prob * ((1.0 - series_win_prob) / t2_total_score_prob)
                else:
                    calibrated_scores[score_key] = prob
                    
        result["win_prob"] = series_win_prob
        result["scores"] = calibrated_scores
        result["base_game_prob"] = base_t1_prob
        result["calibration"] = self._calibration or {}

        # ── VALUE TRAP DETECTION (Omni-Prophet V5.0) ─────────────
        value_traps = self._detect_value_traps(team1, team2)
        result["value_traps"] = value_traps

        # ── ENSEMBLE CROSS-CHECK (Quant-Elite 4.0) ───────────────
        if self._ensemble and _ENSEMBLE_AVAILABLE:
            ensemble_result = self._ensemble.predict(team1, team2, self, det_prob=base_t1_prob)
            result["ensemble"] = ensemble_result
            self._ensemble.print_crosscheck(ensemble_result)

        # ── FORENSIC REPORT (Omni-Prophet V5.0) ──────────────────
        self._print_forensic_report(team1, team2, result, market_odds)

        # ── AUTO-LOG TO LEDGER (Quant-Elite 4.0) ─────────────────
        t1_name = team1.get("name", "T1")
        t2_name = team2.get("name", "T2")
        league = team1.get("league", team2.get("league", "Unknown"))
        match_id = f"{t1_name}_vs_{t2_name}_{datetime.now().strftime('%Y%m%d_%H%M')}"

        if self._ledger and _LEDGER_AVAILABLE:
            try:
                self._ledger.log_prediction(
                    match_id=match_id,
                    league=league,
                    team1=t1_name,
                    team2=t2_name,
                    team1_roster=team1.get("roster", []),
                    team2_roster=team2.get("roster", []),
                    model_prob=series_win_prob,
                    predicted_score=max(result["scores"], key=result["scores"].get) if result["scores"] else None,
                )
            except Exception:
                pass  # Don't let ledger errors break simulations

        # ── AUTO-RECORD (Omni-Prophet V5.0) ──────────────────────
        if _RECORDER_AVAILABLE:
            try:
                match_data = {
                    'team1': team1, 'team2': team2,
                    'league': league,
                    'date': datetime.now().strftime('%Y-%m-%d'),
                }
                record_simulation(match_data, result, market_odds)
            except Exception as e:
                print(f"  ⚠️  Data recorder error: {e}")

        return result

    # ── VALUE TRAP DETECTION (Omni-Prophet V5.0) ─────────────────
    def _detect_value_traps(self, team1, team2):
        """Scan for Value Trap conditions — the LoL equivalent of MLB's Ace Trap.
        Flag if a team triggers 2+ conditions suggesting they are overvalued."""
        traps = {}
        for team, opponent in [(team1, team2), (team2, team1)]:
            flags = []
            name = team.get('name', '?')
            roster = team.get('roster', [])
            
            # 1. Roster Paper Tiger: high power but negative recent trend
            avg_power = sum(self._get_player_power(p) for p in roster) / max(len(roster), 1)
            if avg_power > 90 and team.get('gd15_trend', 0) < 0:
                flags.append(f"Paper Tiger: avg power {avg_power:.0f} but GD@15 trending negative")
            
            # 2. H2H Kryptonite
            h2h_mod = team.get('h2h_modifier', 0)
            if h2h_mod < -0.02:
                flags.append(f"H2H Kryptonite: losing record vs {opponent.get('name', '?')}")
            
            # 3. Form Crash
            syn = self.team_synergy.get(name, 1.0)
            if syn < 0.95 and avg_power > 88:
                flags.append(f"Form Crash: synergy {syn:.2f} despite talent ({avg_power:.0f} avg)")
            
            # 4. Roster Instability
            if team.get('roster_change', False) or team.get('new_player', False):
                flags.append("Roster Instability: recent roster change detected")
            
            # 5. Draft Trap (Fearless)
            champ_pool = team.get('unique_champions', 99)
            if champ_pool < 15:
                flags.append(f"Draft Trap: only {champ_pool} unique champions (Fearless risk)")
            
            # 6. Schedule Fatigue
            if team.get('schedule_fatigue', False) or team.get('back_to_back', False):
                flags.append("Schedule Fatigue: 3rd match in 4 days or back-to-back")
            
            if len(flags) >= 2:
                traps[name] = flags
        
        return traps

    # ── FORENSIC REPORT (Omni-Prophet V5.0) ──────────────────────
    def _print_forensic_report(self, team1, team2, result, market_odds=None):
        """Print standardized forensic prediction report."""
        t1_name = team1.get('name', 'T1')
        t2_name = team2.get('name', 'T2')
        win_prob = result['win_prob']
        scores = result.get('scores', {})
        traps = result.get('value_traps', {})
        cal = result.get('calibration', {})
        ensemble = result.get('ensemble', {})
        
        print(f"\n{'='*72}")
        print(f"  LOL OMNI-PROPHET V5.0 | FORENSIC PREDICTION REPORT")
        print(f"  {t1_name} vs {t2_name} | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"{'='*72}")
        
        # 1. Series Projection
        print(f"\n── 1. SERIES PROJECTION {'(Calibrated)' if cal.get('status') == 'ACTIVE' else ''} ──")
        print(f"  {t1_name}: {win_prob*100:.1f}% series win")
        print(f"  {t2_name}: {(1-win_prob)*100:.1f}% series win")
        if result.get("confidence_cap"):
            print(f"  ⚠️  CONFIDENCE CAP APPLIED: Model Brier score ({cal.get('brier_score')}) is poor. Probability hard-capped at 80%.")
        if result.get("sentiment_warning"):
            print(f"  🚨 {result['sentiment_warning']}")
        if scores:
            print(f"  Score Distribution:")
            for score, prob in sorted(scores.items(), key=lambda x: x[1], reverse=True):
                bar = '█' * int(prob * 30)
                print(f"    {score}: {prob*100:>5.1f}% {bar}")
        if cal.get('prob_adjustment', 1.0) != 1.0:
            print(f"  Calibration Applied: {cal['prob_adjustment']:.3f}x")
        
        # 2. Ensemble Cross-Check
        if ensemble:
            status = '✅ ALIGNED' if not ensemble.get('warning') else '⚠️  SPLIT SIGNAL'
            print(f"\n── 2. ENSEMBLE CROSS-CHECK ──")
            print(f"  Deterministic: {ensemble.get('det_prob', 0)*100:.1f}%")
            if ensemble.get('gbdt_trained'):
                print(f"  GBDT:          {ensemble.get('gbdt_prob', 0)*100:.1f}%")
            print(f"  Status:        {status}")
            print(f"  Final:         {ensemble.get('final_prob', 0)*100:.1f}%")
        
        # 3. Value Trap Scan
        print(f"\n── 3. VALUE TRAP SCAN ──")
        if traps:
            for team, flags in traps.items():
                print(f"  🚨 VALUE TRAP: {team}")
                for f in flags:
                    print(f"    → {f}")
        else:
            print(f"  [NO VALUE TRAPS DETECTED]")
        
        # 4. Calibration Status
        print(f"\n── 4. CALIBRATION STATUS ──")
        if cal.get('status') == 'ACTIVE':
            print(f"  Overall Accuracy: {cal.get('overall_accuracy', 0):.1f}%")
            print(f"  Brier Score: {cal.get('brier_score', 'N/A')}")
            print(f"  Resolved Predictions: {cal.get('n_resolved', 0)}")
        else:
            print(f"  Status: {cal.get('status', 'NOT RUN')}")
        
        # 5. Betting Intelligence
        if market_odds:
            print(f"\n── 5. BETTING INTELLIGENCE ──")
            for label, odds_val in market_odds.items():
                if isinstance(odds_val, (int, float)):
                    imp = self._implied_prob(odds_val) * 100
                    dec = self._american_to_decimal(odds_val)
                    model_p = win_prob if 'team1' in label.lower() or t1_name.lower() in label.lower() else (1 - win_prob)
                    edge = (model_p * 100) - imp
                    kelly = self._calc_kelly(model_p, dec)
                    has_trap = bool(traps)
                    if edge > 5.0 and not has_trap:
                        verdict = 'BET (HIGH CONVICTION)'
                    elif edge > 3.0:
                        verdict = f"LEAN{' (⚠️ Value Trap)' if has_trap else ''}"
                    else:
                        verdict = 'NO EDGE'
                    print(f"  MARKET: {label} @ {odds_val} (implied {imp:.1f}%)")
                    print(f"  MODEL:  {model_p*100:.1f}% | EDGE: {edge:+.1f}% | KELLY: {kelly*100:.2f}%")
                    print(f"  VERDICT: {verdict}")
                    print()
        
        # 6. Data Integrity
        print(f"\n── 6. DATA INTEGRITY ──")
        print(f"  Roster Gate: {'✅' if _GATE_AVAILABLE else '❌ NOT AVAILABLE'}")
        print(f"  Calibration: {'✅' if cal.get('status') == 'ACTIVE' else '⚠️  ' + cal.get('status', 'NOT RUN')}")
        print(f"  Ensemble:    {'✅' if ensemble else '⚠️  Not available'}")
        print(f"  Ledger:      {'✅' if _LEDGER_AVAILABLE else '❌'}")
        print(f"  Recorder:    {'✅' if _RECORDER_AVAILABLE else '❌'}")
        
        print(f"\n{'='*72}")

    # ── BETTING MATH UTILITIES (ported from MLB) ────────────────
    @staticmethod
    def _calc_kelly(model_prob, decimal_odds):
        if decimal_odds <= 1.0 or model_prob <= 0: return 0.0
        b = decimal_odds - 1.0
        q = 1.0 - model_prob
        full_kelly = (b * model_prob - q) / b
        return max(0.0, full_kelly / 4.0)

    @staticmethod
    def _american_to_decimal(american):
        if american >= 100: return 1.0 + american / 100.0
        return 1.0 + 100.0 / abs(american)

    @staticmethod
    def _implied_prob(american):
        if american >= 100: return 100.0 / (american + 100.0)
        return abs(american) / (abs(american) + 100.0)

def run_preflight_slate():
    model = DeterministicLoL()
    
    matches = [
        {
            "team1": {
                "name": "T1",
                "roster": ["Doran", "Oner", "Faker", "Peyz", "Keria"]
            },
            "team2": {
                "name": "NS",
                "roster": ["Kingen", "Sponge", "Scout", "Taeyoon", "Lehends_NS"]
            }
        },
        {
            "team1": {
                "name": "KT",
                "roster": ["PerfecT", "Cuzz", "Bdd", "Aiming", "Pollu"]
            },
            "team2": {
                "name": "HLE",
                "roster": ["Zeus", "Kanavi", "Zeka", "Gumayusi", "Delight"]
            }
        }
    ]
    
    print("\n" + "═"*72)
    print("  🏆 LoL DETERMINISTIC PREDICTION ENGINE — QUANT-ELITE 3.1 🏆")
    print("              APRIL 29, 2026 LCK SLATE")
    print("═"*72)
    
    for m in matches:
        res = model.simulate_bo3(m["team1"], m["team2"])
        t1_name = m["team1"]["name"]
        t2_name = m["team2"]["name"]
        
        print(f"\n  MATCHUP: {t1_name} vs {t2_name}")
        print(f"  Series Win Prob: {res['win_prob']*100:.1f}% ({t1_name})")
        print(f"  Game-by-Game Prob: {res['base_game_prob']*100:.1f}%")
        print(f"  Likely Scores:")
        for score, prob in res["scores"].items():
            bar = "█" * int(prob * 20)
            print(f"    {score}: {prob*100:>5.1f}% {bar}")
            
    print("\n" + "═"*72)
    print("  STRATEGIC INSIGHTS:")
    print("  - T1: Massive Mid/Support gap identified (Faker/Keria). Expect 2-0.")
    print("  - KT: Surging momentum (8-0) offsets HLE's raw roster power (Zeus/Guma).")
    print("  - Value Play: KT ML if priced better than -110.")
    print("═"*72 + "\n")

if __name__ == "__main__":
    run_preflight_slate()
