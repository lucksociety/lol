import math
import random
import sys
import os

# Import the DeterministicLoL engine from the workspace
sys.path.append("/Users/danielreiss/Desktop/Antigravity/LoL")
from models.deterministic_lol import DeterministicLoL

def predict_tsw_cfo():
    model = DeterministicLoL()
    
    # Update player power for the specific rosters based on LCP 2026 Intelligence
    model.player_power.update({
        # Team Secret Whales (Tier S - Undefeated)
        "Pun": 89,
        "Hizto": 90,
        "Dire": 92,
        "Eddie": 91,
        "Bie": 97,
        
        # CTBC Flying Oyster (Tier B - Underperforming)
        "Rest": 88,
        "Shadow": 86,
        "Pout": 85,
        "Doggo": 90,
        "Kino": 85
    })
    
    # Set synergy based on recent form and objective control
    # TSW: 4-0, Split 1 Champs, elite discipline
    # CFO: 1-3, struggling to convert early leads
    model.team_synergy["TSW"] = 1.30
    model.team_synergy["CFO"] = 0.90
    
    match = {
        "team1": {
            "name": "TSW",
            "full_name": "Team Secret Whales",
            "roster": ["Pun", "Hizto", "Dire", "Eddie", "Bie"],
            "tier": "S"
        },
        "team2": {
            "name": "CFO",
            "full_name": "CTBC Flying Oyster",
            "roster": ["Rest", "Shadow", "Pout", "Doggo", "Kino"],
            "tier": "B"
        }
    }
    
    # Run Bo3 Simulation (100k iterations)
    res = model.simulate_bo3(match["team1"], match["team2"])
    
    print("\n" + "═"*72)
    print("  🏆 LCP SPRING 2026 PREDICTION — TSW vs CFO 🏆")
    print("              MAY 03, 2026 - 7:30 AM")
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
    print(f"  - Support Gap: Bie (97) is the highest rated player in the LCP (10.60 KDA) and dictates TSW's macro.")
    print(f"  - Objective Control: TSW leads the league in Dragon (71%) and Baron (74%) control, while CFO is near bottom (33%/25%).")
    print(f"  - Early Aggression vs Scaling: CFO has a 60% FB rate but fails to close. TSW has only 22% FB but wins through superior mid/late macro.")
    print(f"  - Roster Form: TSW is 4-0 (8-1) and looks unbeatable. CFO is 1-3 and still gelling after roster shifts.")
    print(f"  - Prediction: TSW's discipline should overcome CFO's individual talent. Likely 2-0.")
    print("═"*72 + "\n")

if __name__ == "__main__":
    predict_tsw_cfo()
