import math
import random
import sys
import os

# Import the DeterministicLoL engine from the workspace
sys.path.append("/Users/danielreiss/Desktop/Antigravity/LoL")
from models.deterministic_lol import DeterministicLoL

def predict_gx_heretics():
    model = DeterministicLoL()
    
    # Update player power for the EWC Qualifier rosters
    model.player_power.update({
        # GIANTX (GX)
        "Lot": 85,
        "ISMA": 84,
        "Jackies": 88,
        "Noah": 87,
        "Jun": 86,
        
        # Team Heretics (TH)
        "Tracyn": 81,
        "Daglas": 82,
        "Serin": 84,
        "Ice": 88,
        "Way": 87
    })
    
    # Set synergy
    model.team_synergy["GX"] = 1.15
    model.team_synergy["TH"] = 0.80  # Recent instability and poor form
    
    match = {
        "team1": {
            "name": "GIANTX",
            "roster": ["Lot", "ISMA", "Jackies", "Noah", "Jun"],
            "tier": "A"
        },
        "team2": {
            "name": "Team Heretics",
            "roster": ["Tracyn", "Daglas", "Serin", "Ice", "Way"],
            "tier": "B"
        }
    }
    
    # Run Bo3 Simulation (100k iterations)
    res = model.simulate_bo3(match["team1"], match["team2"])
    
    print("\n" + "═"*72)
    print("  🏆 EWC QUALIFIER PREDICTION — GIANTX vs TEAM HERETICS 🏆")
    print("              APRIL 30, 2026 - 2:00 PM")
    print("═"*72)
    
    print(f"\n  MATCHUP: {match['team1']['name']} vs {match['team2']['name']}")
    print(f"  Series Win Prob: {res['win_prob']*100:.1f}% ({match['team1']['name']})")
    print(f"  Base Game Prob: {res['base_game_prob']*100:.1f}%")
    print(f"  Likely Scores:")
    for score, prob in sorted(res["scores"].items(), key=lambda x: x[1], reverse=True):
        bar = "█" * int(prob * 20)
        print(f"    {score}: {prob*100:>5.1f}% {bar}")
            
    print("\n" + "═"*72)
    print("  STRATEGIC INSIGHTS:")
    print("  - Roster Stability vs. Flux: GIANTX has maintained their core for over a year, resulting in superior synergy (1.15). Team Heretics (0.80) is currently struggling with jungle identity after substituting Daglas for Sheo.")
    print("  - Mid Lane Edge: Jackies (88) has been a standout performer for GIANTX. His laning phase against Serin (84) is projected to create mid-game priority that enables ISMA's objective control.")
    print("  - The AD Carry Battle: Noah (87) and Ice (88) are closely matched. This lane will likely be the primary focus of both teams' resources.")
    print("  - Prediction: GIANTX's coordination and mid-lane priority should be enough to overcome the individual mechanics of Heretics' bot lane.")
    print("═"*72 + "\n")

if __name__ == "__main__":
    predict_gx_heretics()
