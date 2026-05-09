import sys
import os
from datetime import datetime

# Add the current directory to sys.path to ensure modules can be imported
sys.path.append(os.getcwd())

from models.deterministic_lol import DeterministicLoL

def run_ktc_drxc_prediction():
    # Initialize the V5.0 Engine
    model = DeterministicLoL()
    
    # ── PHASE 1: RESEARCHED PLAYER POWER (2026 Season) ──────────
    # Based on Deep Research Audit (May 4, 2026)
    model.player_power.update({
        # KT Rolster Challengers (KTC)
        "Sero": 85,
        "Sylvie": 88,
        "Hwichan": 86,
        "FenRir": 85,
        "Ghost": 87,
        
        # Kiwoom DRX Challengers (KRX)
        "Frog": 83,
        "Winner": 84,
        "AKaJe": 84,
        "Jiwoo": 88,
        "Minous": 85
    })
    
    # ── PHASE 2: TEAM SYNERGY & FORM ───────────────────────────
    model.team_synergy["KTC"] = 1.03  # Sylvie dictates pace, high early pressure
    model.team_synergy["KRX"] = 1.01  # Stabilized by Jiwoo's return from main roster
    
    # ── PHASE 3: MATCH CONFIGURATION ───────────────────────────
    match = {
        "team1": {
            "name": "KTC",
            "league": "LCK",
            "roster": ["Sero", "Sylvie", "Hwichan", "FenRir", "Ghost"],
            "side": "blue",         # Assumption: Higher seed/priority gets Blue G1
            "patch_games": 8,       # Active on Patch 16.8
            "aggression_variance": 0.08,
            "h2h_modifier": 0.00    # 1-1 Series H2H in 2026 (Neutral)
        },
        "team2": {
            "name": "KRX",
            "league": "LCK",
            "roster": ["Frog", "Winner", "AKaJe", "Jiwoo", "Minous"],
            "side": "red",
            "patch_games": 6,
            "aggression_variance": 0.10,
            "unique_champions": 18   # Jiwoo/AKaJe have deep pools for Fearless
        }
    }
    
    # Market Intelligence (Decimal to American conversion)
    # KT (1.48) -> -208 | DRX (2.55) -> +155
    market_odds = {
        "KTC Moneyline": -208,
        "KRX Moneyline": 155
    }
    
    # ── PHASE 4: EXECUTE SIMULATION ────────────────────────────
    # 100,000 Iterations as mandated by Protocol V5.0
    res = model.simulate_bo_series(
        match["team1"], 
        match["team2"], 
        best_of=3, 
        iterations=100000,
        market_odds=market_odds
    )
    
    return res

if __name__ == "__main__":
    run_ktc_drxc_prediction()
