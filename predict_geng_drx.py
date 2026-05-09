import math
import random
import sys
import os

# Import the DeterministicLoL engine from the workspace
sys.path.append("/Users/danielreiss/Desktop/Antigravity/LoL")
from models.deterministic_lol import DeterministicLoL

def predict_geng_drx():
    model = DeterministicLoL()
    
    # Update player power for the actual 2026 rosters
    model.player_power.update({
        # Gen.G (2026 Powerhouse)
        "Kiin": 95,
        "Canyon": 97,
        "Chovy": 99,
        "Ruler": 98,
        "Duro": 88,
        
        # DRX (2026 Underdogs)
        "Rich": 86,
        "Willer": 86,
        "ucal": 87,
        "LazyFeel": 87,
        "Andil": 84
    })
    
    # Set synergy
    model.team_synergy["Gen.G"] = 1.25  # High synergy with Ruler/Chovy core
    model.team_synergy["DRX"] = 1.00
    
    match = {
        "team1": {
            "name": "Gen.G",
            "roster": ["Kiin", "Canyon", "Chovy", "Ruler", "Duro"],
            "tier": "S"
        },
        "team2": {
            "name": "DRX",
            "roster": ["Rich", "Willer", "ucal", "LazyFeel", "Andil"],
            "tier": "B"
        }
    }
    
    # Run Bo3 Simulation (100k iterations)
    res = model.simulate_bo3(match["team1"], match["team2"])
    
    print("\n" + "═"*72)
    print("  🏆 LCK SPRING 2026 PREDICTION — GEN.G vs DRX 🏆")
    print("              APRIL 30, 2026 - 4:00 AM")
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
    print("  - Roster Delta: Gen.G averages 95.4 power vs DRX's 86.0. Massive quality gap.")
    print("  - Mid/Jungle: Chovy (99) and Canyon (97) are the world's most dominant duo.")
    print("  - Return of the King: Ruler (98) back on Gen.G provides unmatched late-game stability.")
    print("  - Prediction: Gen.G is overwhelmingly favored. Expect a dominant 2-0 sweep.")
    print("  - Value Play: Gen.G -1.5 (Match Spread) is the standard high-conviction play.")
    print("═"*72 + "\n")

if __name__ == "__main__":
    predict_geng_drx()
