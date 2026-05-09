import math
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.deterministic_lol import DeterministicLoL

def run_simulation():
    engine = DeterministicLoL()
    
    # PHASE 1: RESEARCHED DATA (2026 Season Stats)
    # BFXY: Kangin, Zephyr, FIESTA, Slayer, Luon
    # NS.C: Janus, Mihawk, SeTab, Lucy, Pleata
    
    # Update Player Power based on 2026 Audit
    engine.player_power.update({
        "Kangin": 96, "Zephyr": 80, "FIESTA": 96, "Slayer": 77, "Luon": 74,
        "Janus": 98, "Mihawk": 83, "SeTab": 91, "Lucy": 96, "Pleata": 80
    })
    
    # Update Team Synergy based on Form/Record
    engine.team_synergy.update({
        "BFXY": 0.90,
        "NSC": 1.05
    })
    
    team1 = {
        "name": "BFXY",
        "league": "LCK",
        "roster": ["Kangin", "Zephyr", "FIESTA", "Slayer", "Luon"],
        "side": "blue",  # BFXY Side Selection Game 1
        "patch_games": 8,
        "h2h_modifier": -0.05, # Lost 0-2 in previous H2H
        "gd15_trend": -150, # Recent slide
        "unique_champions": 18,
        "schedule_fatigue": False
    }
    
    team2 = {
        "name": "NSC",
        "league": "LCK",
        "roster": ["Janus", "Mihawk", "SeTab", "Lucy", "Pleata"],
        "side": "red",
        "patch_games": 10,
        "h2h_modifier": 0.05,
        "gd15_trend": 100,
        "unique_champions": 22,
        "schedule_fatigue": False
    }
    
    # Betting Odds from Screenshot
    market_odds = {
        "NSC Moneyline": -192,
        "BFXY Moneyline": +143,
        "NSC -1.5 Spread": +161,
        "FearX +1.5 Spread": -217,
        "Over 2.5 Maps": -109,
        "Under 2.5 Maps": -122
    }
    
    # EXECUTE SIMULATION (100,000 iterations)
    result = engine.simulate_bo3(team1, team2, iterations=100000, market_odds=market_odds)
    
    return result

if __name__ == "__main__":
    run_simulation()
