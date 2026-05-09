import math
import random
import sys
import os

# Import the DeterministicLoL engine from the workspace
sys.path.append("/Users/danielreiss/Desktop/Antigravity/LoL")
from models.deterministic_lol import DeterministicLoL

def predict_up_edg():
    model = DeterministicLoL()
    
    # Update player power for the specific 2026 rosters
    model.player_power.update({
        # EDward Gaming (EDG)
        "Zdz": 84,
        "Xiaohao": 85,
        "Angel": 86,
        "Leave": 85,
        "Parukia": 83,
        
        # Ultra Prime (UP)
        "Liangchen": 81,
        "Grizzly": 84,
        "Saber": 82,
        "Hena": 85,
        "Xiaoxia": 81
    })
    
    # Set synergy
    model.team_synergy["EDG"] = 1.05
    model.team_synergy["UP"] = 1.00
    
    match = {
        "team1": {
            "name": "EDward Gaming",
            "roster": ["Zdz", "Xiaohao", "Angel", "Leave", "Parukia"],
            "tier": "B"
        },
        "team2": {
            "name": "Ultra Prime",
            "roster": ["Liangchen", "Grizzly", "Saber", "Hena", "Xiaoxia"],
            "tier": "C"
        }
    }
    
    # Run Bo3 Simulation (100k iterations)
    res = model.simulate_bo3(match["team1"], match["team2"])
    
    print("\n" + "═"*72)
    print("  🏆 LPL SPLIT 2 2026 PREDICTION — EDG vs ULTRA PRIME 🏆")
    print("              APRIL 30, 2026 - 7:00 AM")
    print("═"*72)
    
    print(f"\n  MATCHUP: {match['team1']['name']} vs {match['team2']['name']}")
    print(f"  Series Win Prob: {res['win_prob']*100:.1f}% ({match['team1']['name']})")
    print(f"  Series Win Prob: {(1-res['win_prob'])*100:.1f}% ({match['name'] if 'name' in match else match['team2']['name']})")
    print(f"  Base Game Prob: {res['base_game_prob']*100:.1f}% (EDG)")
    print(f"  Likely Scores:")
    for score, prob in sorted(res["scores"].items(), key=lambda x: x[1], reverse=True):
        bar = "█" * int(prob * 20)
        print(f"    {score}: {prob*100:>5.1f}% {bar}")
            
    print("\n" + "═"*72)
    print("  STRATEGIC INSIGHTS:")
    print("  - Veteran Experience: Angel (86) provides a significant laning edge over Saber (82).")
    print("  - Jungle Delta: Xiaohao (85) and Grizzly (84) are closely matched, but Angel's priority should enable Xiaohao's invades.")
    print("  - Bot Lane: Leave (85) and Hena (85) are the carry threats for their respective teams. Expect high resource allocation to the bottom side.")
    print("  - Prediction: EDG is favored due to superior mid-lane stability and veteran coordination.")
    print("═"*72 + "\n")

if __name__ == "__main__":
    predict_up_edg()
