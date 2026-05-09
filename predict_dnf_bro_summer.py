import math
import random
import sys
import os

# Import the DeterministicLoL engine from the workspace
sys.path.append("/Users/danielreiss/Desktop/Antigravity/LoL")
from models.deterministic_lol import DeterministicLoL

def predict_dnf_bro_forensic():
    model = DeterministicLoL()
    
    # OVERRIDE PLAYER RATINGS (Based on Summer 2026 data)
    model.player_power.update({
        "Lancer": 85,
        "DDoiV": 86,
        "Flip": 83,
        "Enosh": 81,
        "Peter": 87,
        "DDahyuk": 80,
        "Dinai": 80,
        "Tempester": 80,
        "OddEye": 82,
        "PlanB": 79
    })
    
    # OVERRIDE SYNERGY (Correcting for "Post-Peter" stabilization)
    # The 2-18 historical record (0.88 synergy) is stale.
    # User reports 54% win rate over last 3 months.
    model.team_synergy["DN SOOPers Challengers"] = 1.12
    model.team_synergy["Hanjin Brion Challengers"] = 1.05
    
    match = {
        "team1": {
            "name": "DN SOOPers Challengers",
            "roster": ["Lancer", "DDoiV", "Flip", "Enosh", "Peter"],
            "tier": "A",
            "league": "LCKCL"
        },
        "team2": {
            "name": "Hanjin Brion Challengers",
            "roster": ["DDahyuk", "Dinai", "Tempester", "OddEye", "PlanB"],
            "tier": "B",
            "league": "LCKCL"
        }
    }
    
    # Run Bo3 Simulation (100k iterations)
    # Using require_verification=False to use manual overrides
    res = model.simulate_bo3(match["team1"], match["team2"], require_verification=False)
    
    # The forensic output is already printed by model._print_forensic_report via simulate_bo3
    return res

if __name__ == "__main__":
    predict_dnf_bro_forensic()
