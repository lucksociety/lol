import math
import random
import sys
import os

# Import the DeterministicLoL engine from the workspace
sys.path.append("/Users/danielreiss/Desktop/Antigravity/LoL")
from models.deterministic_lol import DeterministicLoL

def predict_fearx_dk():
    model = DeterministicLoL()
    
    # Update player power for the specific rosters
    model.player_power.update({
        # Dplus KIA
        "Siwoo": 89,
        "Lucid": 88,
        "ShowMaker": 93,
        "Smash": 91,
        "Career": 86,
        
        # BNK FearX
        "Clear": 85,
        "Raptor": 84,
        "VicLa": 87,
        "Diable": 82,
        "Kellin": 88
    })
    
    # Set synergy
    model.team_synergy["DK"] = 1.10
    model.team_synergy["FOX"] = 1.05
    
    match = {
        "team1": {
            "name": "Dplus KIA",
            "roster": ["Siwoo", "Lucid", "ShowMaker", "Smash", "Career"],
            "tier": "A"
        },
        "team2": {
            "name": "BNK FearX",
            "roster": ["Clear", "Raptor", "VicLa", "Diable", "Kellin"],
            "tier": "B"
        }
    }
    
    # Run Bo3 Simulation (100k iterations)
    res = model.simulate_bo3(match["team1"], match["team2"])
    
    print("\n" + "═"*72)
    print("  🏆 LCK SPRING 2026 PREDICTION — DPLUS KIA vs BNK FEARX 🏆")
    print("              APRIL 30, 2026 - 6:00 AM")
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
    print("  - Mid/Jungle Synergy: ShowMaker (93) and Lucid (88) have a massive advantage over VicLa/Raptor.")
    print("  - Bot Lane Delta: Smash (91) is projected to outscale Diable (82) significantly in late-game teamfights.")
    print("  - Kellin Factor: Kellin (88) is the strongest point for FearX, but he is up against his former team's depth.")
    print("  - Prediction: Dplus KIA should win this comfortably, likely 2-0.")
    print("═"*72 + "\n")

if __name__ == "__main__":
    predict_fearx_dk()
