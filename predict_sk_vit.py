import math
import random
import sys
import os

# Import the DeterministicLoL engine from the workspace
sys.path.append("/Users/danielreiss/Desktop/Antigravity/LoL")
from models.deterministic_lol import DeterministicLoL

def predict_sk_vitality():
    model = DeterministicLoL()
    
    # Update player power for May 2, 2026 rosters
    model.player_power.update({
        # Team Vitality (VIT)
        "Naak Nako": 85,
        "Lyncas": 87,
        "Humanoid": 91,
        "Carzzy": 92,
        "Fleshy": 86,
        
        # SK Gaming (SK)
        "Wunder": 84,
        "Skeanz": 81,
        "LIDER": 83,
        "Jopa": 82,
        "Mikyx": 88
    })
    
    # Set synergy
    # Vitality is in peak form (1.15)
    model.team_synergy["VIT"] = 1.15
    # SK is struggling to find coordination (0.85)
    model.team_synergy["SK"] = 0.85
    
    match = {
        "team1": {
            "name": "Team Vitality",
            "roster": ["Naak Nako", "Lyncas", "Humanoid", "Carzzy", "Fleshy"],
            "tier": "S"
        },
        "team2": {
            "name": "SK Gaming",
            "roster": ["Wunder", "Skeanz", "LIDER", "Jopa", "Mikyx"],
            "tier": "D"
        }
    }
    
    # Run Bo3 Simulation (100k iterations)
    res = model.simulate_bo3(match["team1"], match["team2"])
    
    print("\n" + "═"*72)
    print("  🏆 LEC 2026 SPRING PREDICTION — TEAM VITALITY vs SK GAMING 🏆")
    print("                MAY 2, 2026 - 9:00 PM CET")
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
    print(f"  - The David vs Goliath: Vitality (6-1) is contending for the top spot, while SK (2-6) is fighting to avoid the bottom 2. The statistical gap between these teams is the largest in the split.")
    print(f"  - Lane Dominance: Humanoid (91) and Carzzy (92) represent a level of mechanical proficiency that SK's mid/bot duo cannot match. Even with Mikyx (88) attempting to roam, Vitality's laning phase is projected to be overwhelmingly positive.")
    print(f"  - Early Game Rating (EGR): Vitality leads the league (61.7). They average a +1037 gold lead @ 15, whereas SK averages a league-worst -1496 gold lead @ 15. This match is likely to be decided before the 20-minute mark.")
    print(f"  - Champion Pool Friction: SK's success is highly dependent on LIDER (83) finding a niche pick (Melee mids/Assassins). Vitality's structured drafting and Humanoid's deep pool make this a difficult win condition to execute.")
    print(f"  - Prediction: Vitality's superior EGR and raw roster power should result in a dominant 2-0 sweep. SK lacks the objective control (Dragons/Barons) to mount a comeback once behind.")
    print("═"*72 + "\n")

if __name__ == "__main__":
    predict_sk_vitality()
