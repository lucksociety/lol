
import sys
import os
from datetime import datetime

# Add the workspace to path to import models
sys.path.append('/Users/danielreiss/Desktop/Antigravity/LoL')

from models.deterministic_lol import DeterministicLoL

def run_simulation():
    # Initialize Engine
    sim = DeterministicLoL()

    # Phase 1: Team & Player Data
    # ── Update player_power manually (Fallback/Override) ──
    # Brion Challengers (BROC)
    sim.player_power["DDahyuk"] = 81
    sim.player_power["Dinai"] = 83
    sim.player_power["Tempester"] = 88
    sim.player_power["OddEye"] = 90
    sim.player_power["PlanB"] = 82

    # Gen.G Global Academy (GENA)
    sim.player_power["Ripple"] = 77
    sim.player_power["Courage"] = 80
    sim.player_power["Kemish"] = 87
    sim.player_power["MUDAI"] = 82
    sim.player_power["SIRIUSS"] = 81

    # ── Update team_synergy ──
    sim.team_synergy["BROC"] = 1.05 # Won last H2H, better record
    sim.team_synergy["GENA"] = 0.98 # Lower record, lost last H2H

    # Construct Team Objects
    team1 = {
        "name": "BROC",
        "league": "LCK",
        "roster": ["DDahyuk", "Dinai", "Tempester", "OddEye", "PlanB"],
        "side": "blue", # Side selection for Game 1 (usually higher seed/side choice)
        "h2h_modifier": 0.05, # +5% edge from 2-1 April victory
        "patch_games": 4, # Estimated games on 16.8
        "gd15_trend": 150 # Positive trend
    }

    team2 = {
        "name": "GENA",
        "league": "LCK",
        "roster": ["Ripple", "Courage", "Kemish", "MUDAI", "SIRIUSS"],
        "side": "red",
        "patch_games": 4,
        "gd15_trend": -300, # Negative trend
        "unique_champions": 18 # Fearless format depth
    }

    # Market Odds (Decimal to American conversion for the engine's internal math)
    # 1.31 -> -323
    # 3.125 -> +212
    market_odds = {
        "BROC ML": -323,
        "GENA ML": 212
    }

    # Run Simulation (100,000 iterations)
    # The engine handles Calibration and Roster Verification internally
    results = sim.simulate_bo3(team1, team2, iterations=100000, market_odds=market_odds)

if __name__ == "__main__":
    run_simulation()
