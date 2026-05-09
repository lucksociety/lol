import math
import random
import sys
import os

# Import the DeterministicLoL engine from the workspace
sys.path.append("/Users/danielreiss/Desktop/Antigravity/LoL")
from models.deterministic_lol import DeterministicLoL

def predict_tt_lgd():
    model = DeterministicLoL()
    
    # Update player power for the specific rosters
    model.player_power.update({
        # TT Gaming
        "Keshi": 82,
        "Junhao": 81,
        "Heru": 83,
        "Ryan3": 85,
        "Feather": 80,
        
        # LGD Gaming
        "sasi": 81,
        "Heng": 84,
        "Tangyuan": 86,
        "Shaoye": 85,
        "ycx": 82
    })
    
    # Set synergy
    model.team_synergy["TT"] = 0.95
    model.team_synergy["LGD"] = 1.05
    
    match = {
        "team1": {
            "name": "TT Gaming",
            "roster": ["Keshi", "Junhao", "Heru", "Ryan3", "Feather"],
            "tier": "C"
        },
        "team2": {
            "name": "LGD Gaming",
            "roster": ["sasi", "Heng", "Tangyuan", "Shaoye", "ycx"],
            "tier": "B"
        }
    }
    
    # Run Bo3 Simulation (100k iterations)
    res = model.simulate_bo3(match["team1"], match["team2"])
    
    # Invert for TT vs LGD (The model calculates team1 win prob)
    # But for display, I want to show both
    
    print("\n" + "═"*72)
    print("  🏆 LPL SPLIT 2 2026 PREDICTION — TT GAMING vs LGD GAMING 🏆")
    print("              APRIL 30, 2026 - 5:00 AM")
    print("═"*72)
    
    print(f"\n  MATCHUP: {match['team1']['name']} vs {match['team2']['name']}")
    print(f"  Series Win Prob: {res['win_prob']*100:.1f}% ({match['team1']['name']})")
    print(f"  Series Win Prob: {(1-res['win_prob'])*100:.1f}% ({match['team2']['name']})")
    print(f"  Base Game Prob: {res['base_game_prob']*100:.1f}% (TT)")
    print(f"  Likely Scores:")
    for score, prob in sorted(res["scores"].items(), key=lambda x: x[1], reverse=True):
        bar = "█" * int(prob * 20)
        print(f"    {score}: {prob*100:>5.1f}% {bar}")
            
    print("\n" + "═"*72)
    print("  STRATEGIC INSIGHTS:")
    print("  - Mid Gap: Tangyuan (86) is the centerpiece for LGD. His laning phase is projected to be the deciding factor.")
    print("  - Jungle Tempo: Heng (84) has a distinct experience edge over Junhao (81), likely leading to early dragon control.")
    print("  - TT Win Condition: Ryan3 (85) must reach his 3-item spike ahead of Shaoye (85). TT's 0.95 synergy reflects their struggles in late-game coordination.")
    print("  - Prediction: LGD Gaming is the statistical favorite in a likely 3-game series.")
    print("═"*72 + "\n")

if __name__ == "__main__":
    predict_tt_lgd()
