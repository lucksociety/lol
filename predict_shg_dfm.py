import math
import random
import sys
import os

# Import the DeterministicLoL engine from the workspace
sys.path.append("/Users/danielreiss/Desktop/Antigravity/LoL")
from models.deterministic_lol import DeterministicLoL

def predict_shg_dfm():
    model = DeterministicLoL()
    
    # Update player power for the specific rosters based on LCP 2026 Intelligence
    model.player_power.update({
        # Fukuoka SoftBank HAWKS (Tier S)
        "Evi": 91,
        "van": 92,
        "Aria": 94,
        "Marble": 96,
        "Vsta": 90,
        
        # DetonatioN FocusMe (Tier D)
        "Momo": 74,
        "Citrus": 78,
        "Fisher": 80,
        "Kakkun": 79,
        "Woody": 84
    })
    
    # Set synergy based on recent form and GD@15
    # SHG has +1262 GD@15 (Elite)
    # DFM has -1761 GD@15 (Crisis)
    model.team_synergy["SHG"] = 1.25
    model.team_synergy["DFM"] = 0.80
    
    match = {
        "team1": {
            "name": "SHG",
            "full_name": "Fukuoka SoftBank HAWKS Gaming",
            "roster": ["Evi", "van", "Aria", "Marble", "Vsta"],
            "tier": "S"
        },
        "team2": {
            "name": "DFM",
            "full_name": "DetonatioN FocusMe",
            "roster": ["Momo", "Citrus", "Fisher", "Kakkun", "Woody"],
            "tier": "D"
        }
    }
    
    # Run Bo3 Simulation (100k iterations)
    res = model.simulate_bo3(match["team1"], match["team2"])
    
    print("\n" + "═"*72)
    print("  🏆 LCP SPRING 2026 PREDICTION — SHG vs DFM 🏆")
    print("              MAY 03, 2026 - 5:00 AM")
    print("═"*72)
    
    print(f"\n  MATCHUP: {match['team1']['full_name']} vs {match['team2']['full_name']}")
    print(f"  Series Win Prob: {res['win_prob']*100:.1f}% ({match['team1']['name']})")
    print(f"  Base Game Prob: {res['base_game_prob']*100:.1f}%")
    print(f"  Likely Scores:")
    for score, prob in sorted(res["scores"].items(), key=lambda x: x[1], reverse=True):
        bar = "█" * int(prob * 20)
        print(f"    {score}: {prob*100:>5.1f}% {bar}")
            
    print("\n" + "═"*72)
    print("  STRATEGIC INSIGHTS:")
    print(f"  - Early Game Delta: SHG leads the league with +1262 GD@15, while DFM is last at -1761.")
    print(f"  - Bot Lane Mismatch: Marble (96) vs Kakkun (79) is the largest gap on the rift.")
    print(f"  - Top Lane Gap: Evi (91) is a brick wall compared to Momo's (74) struggling performance (0.67 KDA).")
    print(f"  - Momentum: SHG is 3-1 (7-2 games) whereas DFM is 0-4 (2-8 games) in a historic slump.")
    print(f"  - Prediction: Absolute dominance from SHG. High confidence in a 2-0 sweep.")
    print("═"*72 + "\n")

if __name__ == "__main__":
    predict_shg_dfm()
