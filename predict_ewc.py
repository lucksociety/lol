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
    
    matches = [
        {
            "team1": {"name": "SK", "roster": ["Wunder", "Skeanz", "LIDER", "Jopa", "Mikyx"]},
            "team2": {"name": "TH", "roster": ["Tracyn", "Sheo", "Serin", "Ice", "Way"]}
        },
        {
            "team1": {"name": "VIT", "roster": ["Naak Nako", "Lyncas", "Humanoid", "Carzzy", "Fleshy"]},
            "team2": {"name": "SLY", "roster": ["Kryze", "Zicssi", "Jool", "Aetinoth", "Piero"]}
        }
    ]
    
    print("\n" + "═"*72)
    print("  🏆 EWC QUALIFIER PREDICTION — EMEA BRACKET BREAKDOWN 🏆")
    print("              APRIL 28, 2026")
    print("═"*72)
    
    for match in matches:
        res = model.simulate_bo3(match["team1"], match["team2"])
        t1 = match["team1"]["name"]
        t2 = match["team2"]["name"]
        
        print(f"\n  MATCHUP: {t1} vs {t2}")
        print(f"  Series Win Prob: {res['win_prob']*100:.1f}% ({t1})")
        print(f"  Game-by-Game Prob: {res['game_prob']*100:.1f}%")
        print(f"  Likely Scores:")
        for score, prob in res["scores"].items():
            bar = "█" * int(prob * 20)
            print(f"    {score}: {prob*100:>5.1f}% {bar}")
            
    print("\n" + "═"*72)
    print("  STRATEGIC INSIGHTS:")
    print("  - VIT vs SLY: The 'David vs Goliath' matchup. Solary is the most dangerous")
    print("    ERL team (EMEA Masters Champs). Synergy (1.40) keeping them alive.")
    print("  - Carry Gap: Humanoid/Carzzy (94/93) vs Jool/Aetinoth (84/83).")
    print("  - Value Play: SLY +1.5 Map Handicap is viable if odds > +120.")
    print("═"*72 + "\n")

if __name__ == "__main__":
    run_prediction()
