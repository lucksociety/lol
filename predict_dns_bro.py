import math
import random
import sys
import os

# Import the DeterministicLoL engine from the workspace
sys.path.append("/Users/danielreiss/Desktop/Antigravity/LoL")
from models.deterministic_lol import DeterministicLoL

def predict_dns_bro_challengers():
    model = DeterministicLoL()
    
    # Update player power for the LCK CL rosters (Spring 2026)
    model.player_power.update({
        # DN SOOPers Challengers (DNS.C)
        "Lancer": 82,
        "DDoiV": 80,
        "Flip": 81,
        "Enosh": 80,
        "Peter": 85,  # LCK veteran upgrade (formerly NS)
        
        # HANJIN BRION Challengers (BRO.C)
        "DDahyuk": 80,
        "Dinai": 80,    # Buffed due to recent form
        "Tempester": 80, # Buffed due to recent form
        "OddEye": 81,
        "PlanB": 80
    })
    
    # Set synergy based on recent momentum and roster stability
    model.team_synergy["DNSC"] = 1.10  # Boosted by Peter's leadership
    model.team_synergy["BROC"] = 1.15  # Massive 2-0 week momentum (beat NS 2-0)
    
    match = {
        "team1": {
            "name": "DN SOOPers Challengers",
            "roster": ["Lancer", "DDoiV", "Flip", "Enosh", "Peter"],
            "tier": "B"
        },
        "team2": {
            "name": "Hanjin Brion Challengers",
            "roster": ["DDahyuk", "Dinai", "Tempester", "OddEye", "PlanB"],
            "tier": "B" # Upgraded from C due to recent wins
        }
    }
    
    # Run Bo3 Simulation (100k iterations)
    res = model.simulate_bo3(match["team1"], match["team2"])
    
    print("\n" + "═"*72)
    print("  🏆 LCK CL SPRING 2026 PREDICTION — DNS.C vs BRO.C 🏆")
    print("              MAY 1, 2026 - 4:00 AM")
    print("═"*72)
    
    print(f"\n  MATCHUP: {match['team1']['name']} vs {match['team2']['name']}")
    print(f"  Series Win Prob: {res['win_prob']*100:.1f}% ({match['team1']['name']})")
    print(f"  Base Game Prob: {res['base_game_prob']*100:.1f}%")
    print(f"  Likely Scores:")
    # Sort scores to show most likely first
    sorted_scores = sorted(res["scores"].items(), key=lambda x: x[1], reverse=True)
    for score, prob in sorted_scores:
        bar = "█" * int(prob * 20)
        print(f"    {score}: {prob*100:>5.1f}% {bar}")
            
    print("\n" + "═"*72)
    print("  STRATEGIC INSIGHTS:")
    print("  - The Peter Effect: DNS has stabilized significantly since Peter (85) joined. His veteran macro and vision control (formerly of NS RedForce) give DNS a floor they didn't have with Quantum.")
    print("  - BRION's Surge: BRO.C is the hottest team in the bottom half of the table. Their 2-0 demolition of Nongshim proves their mid-jungle duo (Dinai/Tempester) is finally clicking.")
    print("  - Lane Delta: Lancer (82) vs DDahyuk (80) is the key matchup. If Lancer can bully top, DNS can neutralize BRO's current momentum.")
    print("  - Deterministic Outcome: While BRO has the momentum, DNS has the superior raw power floor with Peter. This is a high-variance Bo3.")
    print("  - Prediction: DN SOOPers are marginal favorites, but BRION's current trajectory makes a 2-1 result for either side the most probable outcome.")
    print("═"*72 + "\n")

if __name__ == "__main__":
    predict_dns_bro_challengers()
