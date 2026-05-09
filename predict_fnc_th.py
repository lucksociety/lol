import math
import random
import sys
import os

# Import the DeterministicLoL engine from the workspace
sys.path.append("/Users/danielreiss/Desktop/Antigravity/LoL")
from models.deterministic_lol import DeterministicLoL

def predict_fnc_heretics():
    model = DeterministicLoL()
    
    # Update player power for May 2, 2026 rosters
    model.player_power.update({
        # Fnatic (FNC)
        "Empyros": 83,
        "Razork": 88,
        "Vladi": 84,
        "Upset": 89,
        "Lospa": 82,
        
        # Team Heretics (TH)
        "Tracyn": 81,
        "Daglas": 82,
        "Serin": 84,
        "Ice": 88,
        "Way": 87
    })
    
    # Set synergy
    # Fnatic is stable but struggling to close (1.05)
    model.team_synergy["FNC"] = 1.05
    # Heretics has a new jungle and is on a massive losing streak (0.75)
    model.team_synergy["TH"] = 0.75 
    
    match = {
        "team1": {
            "name": "Fnatic",
            "roster": ["Empyros", "Razork", "Vladi", "Upset", "Lospa"],
            "tier": "C"
        },
        "team2": {
            "name": "Team Heretics",
            "roster": ["Tracyn", "Daglas", "Serin", "Ice", "Way"],
            "tier": "D"
        }
    }
    
    # Run Bo3 Simulation (100k iterations)
    res = model.simulate_bo3(match["team1"], match["team2"])
    
    print("\n" + "═"*72)
    print("  🏆 LEC 2026 SPRING PREDICTION — FNATIC vs TEAM HERETICS 🏆")
    print("                MAY 2, 2026 - 6:00 PM CET")
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
    print(f"  - The Battle of the Basements: Both teams are in the bottom half of the standings. Fnatic (2-5) is looking to break a slump, while Heretics (0-6) is desperate for their first win of the split.")
    print(f"  - Jungle Gap: Razork (88) is the primary engine for Fnatic. Against the newly promoted Daglas (82), Razork should find significant early-game advantages in pathing and objective control.")
    print(f"  - Bot Lane Focus: Upset (89) remains one of the most mechanically gifted ADCs in the west. His matchup against Ice (88) is the most competitive lane, but Lospa (82) vs Way (87) favors Heretics slightly in support utility.")
    print(f"  - Mid-Late Collapse Factor: Both teams have terrible MLR (Mid-Late Rating), but Heretics is statistically the worst in the league (-24.8). If Fnatic gains even a slight lead, Heretics is unlikely to find the coordination to come back.")
    print(f"  - Prediction: Fnatic's superior individual talent in the jungle and mid lane, combined with Heretics' ongoing roster instability, points to a comfortable Fnatic victory.")
    print("═"*72 + "\n")

if __name__ == "__main__":
    predict_fnc_heretics()
