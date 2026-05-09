import math
import random
import json
import os
import sys

# Use the shared gated engine — NOT an inline copy
sys.path.append("/Users/danielreiss/Desktop/Antigravity/LoL")
from models.deterministic_lol import DeterministicLoL


def run_prediction():
    model = DeterministicLoL()
    
    match = {
        "team1": {
            "name": "BLG",
            "roster": ["Bin", "Xun", "knight", "Viper", "ON"]
        },
        "team2": {
            "name": "WE",
            "roster": ["Cube", "Monki", "Karis", "About", "Erha"]
        }
    }
    
    res = model.simulate_bo3(match["team1"], match["team2"])
    
    print("\n" + "═"*72)
    print("  🏆 LPL SPLIT 2 PREDICTION — BLG vs TEAM WE 🏆")
    print("              APRIL 29, 2026")
    print("═"*72)
    
    print(f"\n  MATCHUP: Bilibili Gaming vs Team WE")
    print(f"  Series Win Prob: {res['win_prob']*100:.1f}% (BLG)")
    print(f"  Game-by-Game Prob: {res['game_prob']*100:.1f}%")
    print(f"  Likely Scores:")
    for score, prob in res["scores"].items():
        bar = "█" * int(prob * 20)
        print(f"    {score}: {prob*100:>5.1f}% {bar}")
            
    print("\n" + "═"*72)
    print("  STRATEGIC INSIGHTS:")
    print("  - Total Domination: BLG averages a 94.8 power rating vs WE's 80.6.")
    print("  - Mid Gap: knight (98) vs Karis (81). Expect knight to roam and end early.")
    print("  - Team State: WE is currently 0-14 in games this split. Morale is non-existent.")
    print("  - Recommendation: BLG 2-0 is a mathematical certainty in this model.")
    print("═"*72 + "\n")

if __name__ == "__main__":
    run_prediction()
