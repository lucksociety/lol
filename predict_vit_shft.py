import math
import random
import sys
import os

# Import the DeterministicLoL engine from the workspace
sys.path.append("/Users/danielreiss/Desktop/Antigravity/LoL")
from models.deterministic_lol import DeterministicLoL

def predict_vit_shifters():
    model = DeterministicLoL()
    
    # Update player power for the EWC Qualifier rosters
    model.player_power.update({
        # Team Vitality (VIT)
        "Naak Nako": 86,
        "Lyncas": 89,
        "Humanoid": 94,
        "Carzzy": 93,
        "Fleshy": 85,
        
        # Shifters (SHFT)
        "Rooster": 83,
        "Boukada": 82,
        "nuc": 86,
        "Paduck": 84,
        "Trymbi": 89
    })
    
    # Set synergy
    model.team_synergy["VIT"] = 1.05
    model.team_synergy["SHFT"] = 1.10  # Trymbi/nuc veteran core
    
    match = {
        "team1": {
            "name": "Team Vitality",
            "roster": ["Naak Nako", "Lyncas", "Humanoid", "Carzzy", "Fleshy"],
            "tier": "A"
        },
        "team2": {
            "name": "Shifters",
            "roster": ["Rooster", "Boukada", "nuc", "Paduck", "Trymbi"],
            "tier": "B"
        }
    }
    
    # Run Bo3 Simulation (100k iterations)
    res = model.simulate_bo3(match["team1"], match["team2"])
    
    print("\n" + "═"*72)
    print("  🏆 EWC QUALIFIER PREDICTION — VITALITY vs SHIFTERS 🏆")
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
    print("  - Carry Gap: Humanoid (94) and Carzzy (93) are LEC-tier superstars. Their mechanical ceiling is significantly higher than nuc/Paduck.")
    print("  - The Trymbi Factor: Trymbi (89) is the primary playmaker for Shifters. If he can create early rotations with Boukada, Shifters can punish Vitality's occasional mid-game overextensions.")
    print("  - Jungle Delta: Lyncas (89) has been the standout performer for Vitality. His early-game pathing is projected to outpace Boukada (82).")
    print("  - Prediction: Vitality is the heavy favorite due to individual skill gaps across all carry roles.")
    print("═"*72 + "\n")

if __name__ == "__main__":
    predict_vit_shifters()
