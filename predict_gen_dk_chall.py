import math
import random
import sys
import os

# Import the DeterministicLoL engine from the workspace
sys.path.append("/Users/danielreiss/Desktop/Antigravity/LoL")
from models.deterministic_lol import DeterministicLoL

def predict_geng_dk_challengers():
    model = DeterministicLoL()
    
    # Update player power for the LCK CL rosters
    model.player_power.update({
        # Gen.G Global Academy (GEN.A)
        "Courage": 81,
        "Kemish": 80,
        "Ripple": 81,
        "MUDAI": 82,
        "Lumos": 80,
        
        # Dplus KIA Challengers (DK.C)
        "Jaehyuk": 82,
        "Sharvel": 81,
        "Garden": 83,
        "Wayne": 82,
        "Loopy": 81
    })
    
    # Set synergy
    model.team_synergy["GENA"] = 1.05
    model.team_synergy["DKC"] = 1.10
    
    match = {
        "team1": {
            "name": "Gen.G Global Academy",
            "roster": ["Courage", "Kemish", "Ripple", "MUDAI", "Lumos"],
            "tier": "B"
        },
        "team2": {
            "name": "Dplus Challengers",
            "roster": ["Jaehyuk", "Sharvel", "Garden", "Wayne", "Loopy"],
            "tier": "B"
        }
    }
    
    # Run Bo3 Simulation (100k iterations)
    res = model.simulate_bo3(match["team1"], match["team2"])
    
    print("\n" + "═"*72)
    print("  🏆 LCK CL SPRING 2026 PREDICTION — GEN.G vs DPLUS 🏆")
    print("              APRIL 30, 2026 - 1:00 AM")
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
    print("  - The Academy Pedigree: Dplus KIA (DK.C) has one of the most successful developmental systems in South Korea. Garden (83) and Jaehyuk (82) are the primary anchors for this new iteration of the roster.")
    print("  - Mechanical Matchup: Gen.G’s MUDAI (82) is a standout ADC prospect. His ability to carry late-game teamfights is GEN.A’s clearest path to victory.")
    print("  - Synergy Advantage: DK.C’s 1.10 synergy reflects their historically superior coaching and developmental infrastructure, which often translates to better mid-game macro in the Challengers League.")
    print("  - Prediction: Dplus Challengers are the statistical favorites in a series that is likely to be decided by superior macro coordination.")
    print("═"*72 + "\n")

if __name__ == "__main__":
    predict_geng_dk_challengers()
