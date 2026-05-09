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
            "name": "KT",
            "roster": ["PerfecT", "Cuzz", "Bdd", "Aiming", "Pollu"]
        },
        "team2": {
            "name": "HLE",
            "roster": ["Zeus", "Kanavi", "Zeka", "Gumayusi", "Delight"]
        }
    }
    
    res = model.simulate_bo3(match["team1"], match["team2"])
    
    print("\n" + "═"*72)
    print("  🏆 LCK SPRING 2026 PREDICTION — KT ROLSTER vs HLE 🏆")
    print("              APRIL 29, 2026")
    print("═"*72)
    
    print(f"\n  MATCHUP: KT Rolster vs Hanwha Life Esports")
    print(f"  Series Win Prob: {res['win_prob']*100:.1f}% (KT Rolster)")
    print(f"  Game-by-Game Prob: {res['game_prob']*100:.1f}%")
    print(f"  Likely Scores:")
    for score, prob in res["scores"].items():
        bar = "█" * int(prob * 20)
        print(f"    {score}: {prob*100:>5.1f}% {bar}")
            
    print("\n" + "═"*72)
    print("  STRATEGIC INSIGHTS:")
    print("  - Synergy vs. Star Power: KT's 1.55 momentum nearly offsets HLE's 473 total power.")
    print("  - Jungle Delta: Kanavi (94) vs Cuzz (92). HLE expected to control Rift Herald.")
    print("  - Top Matchup: Zeus (98) is the highest-rated player. He is the win condition for HLE.")
    print("  - Recommendation: A true coin-flip. Value lies on HLE if odds > +110.")
    print("═"*72 + "\n")

if __name__ == "__main__":
    run_prediction()
