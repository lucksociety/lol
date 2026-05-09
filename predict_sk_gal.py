import math
import random
import sys
import os

# Import the DeterministicLoL engine from the workspace
sys.path.append("/Users/danielreiss/Desktop/Antigravity/LoL")
from models.deterministic_lol import DeterministicLoL

def predict_sk_galions():
    model = DeterministicLoL()
    
    # Update player power for the EWC Qualifier rosters
    model.player_power.update({
        # SK Gaming (LEC)
        "Wunder": 86,
        "Skeanz": 83,
        "SlowQ": 84,
        "Jopa": 85,
        "Mikyx": 93,
        
        # Galions (LFL)
        "Carlsen": 85,
        "Thayger": 82,
        "OMON": 83,
        "Harpoon": 84,
        "Zoelys": 86
    })
    
    # Set synergy
    model.team_synergy["SK"] = 1.10
    model.team_synergy["Galions"] = 1.20  # LFL teams typically have high coordination
    
    match = {
        "team1": {
            "name": "SK Gaming",
            "roster": ["Wunder", "Skeanz", "SlowQ", "Jopa", "Mikyx"],
            "tier": "A"
        },
        "team2": {
            "name": "Galions",
            "roster": ["Carlsen", "Thayger", "OMON", "Harpoon", "Zoelys"],
            "tier": "B"
        }
    }
    
    # Run Bo3 Simulation (100k iterations)
    res = model.simulate_bo3(match["team1"], match["team2"])
    
    print("\n" + "═"*72)
    print("  🏆 EWC QUALIFIER PREDICTION — SK GAMING vs GALIONS 🏆")
    print("              APRIL 30, 2026 - 11:00 AM")
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
    print("  - Support Gap: Mikyx (93) is the primary win condition for SK. His roaming and vision control are projected to neutralize Zoelys (86).")
    print("  - Mid Lane Variable: SlowQ (84) is a rookie sub. If OMON (83) can find a laning advantage, Galions could steal a game.")
    print("  - Top Lane: Wunder (86) vs Carlsen (85) is the most competitive matchup. Carlsen is a rising LFL star.")
    print("  - Prediction: SK Gaming's LEC experience and Mikyx's leadership should secure the series.")
    print("═"*72 + "\n")

if __name__ == "__main__":
    predict_sk_galions()
