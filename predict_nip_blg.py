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
            "name": "NIP",
            "roster": ["HOYA", "Guwon", "Care", "Assum", "Zhuo"]
        },
        "team2": {
            "name": "BLG",
            "roster": ["Bin", "Xun", "knight", "Viper", "ON"]
        }
    }
    
    res = model.simulate_bo3(match["team1"], match["team2"])
    
    # Flip for BLG perspective
    blg_win_prob = 1 - res["win_prob"]
    blg_game_prob = 1 - res["game_prob"]
    flipped_scores = {
        "2-0": res["scores"]["0-2"],
        "2-1": res["scores"]["1-2"],
        "0-2": res["scores"]["2-0"],
        "1-2": res["scores"]["2-1"]
    }

    print("\n" + "═"*72)
    print("  🏆 LPL 2026 SPLIT 2 PREDICTION — BLG vs NIP 🏆")
    print("              MAY 03, 2026")
    print("═"*72)
    
    print(f"\n  MATCHUP: Bilibili Gaming vs Ninjas in Pyjamas")
    print(f"  Series Win Prob: {blg_win_prob*100:.1f}% (BLG)")
    print(f"  Game-by-Game Prob: {blg_game_prob*100:.1f}%")
    print(f"  Likely Scores:")
    for score, prob in flipped_scores.items():
        bar = "█" * int(prob * 20)
        print(f"    {score}: {prob*100:>5.1f}% {bar}")
            
    print("\n" + "═"*72)
    print("  STRATEGIC INSIGHTS:")
    print("  - Revenge Factor: BLG was humiliated 0-2 by NiP on April 23. Bin and knight are expected to play with extreme aggression to reclaim their status.")
    print("  - Solo Lane Delta: Bin (96) vs HOYA (86) is the primary win condition. BLG's top-side pressure will likely force NiP's jungle to stay top, leaving Viper (94) to scale freely.")
    print("  - Statistical Anomaly: NiP's 66.7% win rate is boosted by their recent form, but their historical match-loss rate against S-tier teams in BO3 remains high.")
    print("  - Recommendation: BLG 2-1 or 2-0. BLG's talent floor is too high for a repeat upset, but NiP's current momentum makes a 2-1 more probable than the raw power gap suggests.")
    print("═"*72 + "\n")

if __name__ == "__main__":
    run_prediction()
