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
            "name": "JDG",
            "roster": ["Xiaoxu", "JunJia", "HongQ", "GALA", "Vampire"]
        },
        "team2": {
            "name": "NIP",
            "roster": ["Hoya", "Guwon", "Care", "Assum", "Zhuo"]
        }
    }
    
    res = model.simulate_bo3(match["team1"], match["team2"])
    
    print("\n" + "═"*72)
    print("  🏆 LPL SPLIT 2 PREDICTION — JD GAMING vs NIP 🏆")
    print("              APRIL 29, 2026")
    print("═"*72)
    
    print(f"\n  MATCHUP: JD Gaming vs Ninjas in Pyjamas")
    print(f"  Series Win Prob: {res['win_prob']*100:.1f}% (JD Gaming)")
    print(f"  Game-by-Game Prob: {res['game_prob']*100:.1f}%")
    print(f"  Likely Scores:")
    for score, prob in res["scores"].items():
        bar = "█" * int(prob * 20)
        print(f"    {score}: {prob*100:>5.1f}% {bar}")
            
    print("\n" + "═"*72)
    print("  STRATEGIC INSIGHTS:")
    print("  - Bot Gap: GALA (94) is the premier ADC in this matchup. NiP must shut him down.")
    print("  - Momentum: JDG is on a 2-series win streak (both 2-0). NiP has lost 2 of last 3.")
    print("  - Previous Match: NiP won 2-0 on Apr 17, but JDG has significantly improved since.")
    print("  - Recommendation: JDG 2-1 or 2-0. Their upward trajectory is too strong to ignore.")
    print("═"*72 + "\n")

if __name__ == "__main__":
    run_prediction()
