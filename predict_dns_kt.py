import math
import random
import sys
import os

# Import the DeterministicLoL engine from the workspace
sys.path.append("/Users/danielreiss/Desktop/Antigravity/LoL")
from models.deterministic_lol import DeterministicLoL

def predict_dns_kt_challengers():
    model = DeterministicLoL()
    
    # Update player power for the LCK CL rosters
    model.player_power.update({
        # KT Rolster Challengers (KT.C)
        "Sero": 81,
        "Sylvie": 82,
        "hwichan": 80,
        "FenRir": 81,
        "Effort": 85,
        
        # DN SOOPers Challengers (DNS.C)
        "Lancer": 82,
        "DDoiV": 80,
        "Flip": 81,
        "Enosh": 80,
        "Quantum": 82
    })
    
    # Set synergy
    model.team_synergy["KTC"] = 1.10
    model.team_synergy["DNSC"] = 1.05
    
    match = {
        "team1": {
            "name": "KT Rolster Challengers",
            "roster": ["Sero", "Sylvie", "hwichan", "FenRir", "Effort"],
            "tier": "B"
        },
        "team2": {
            "name": "DN SOOPers Challengers",
            "roster": ["Lancer", "DDoiV", "Flip", "Enosh", "Quantum"],
            "tier": "B"
        }
    }
    
    # Run Bo3 Simulation (100k iterations)
    res = model.simulate_bo3(match["team1"], match["team2"])
    
    print("\n" + "═"*72)
    print("  🏆 LCK CL SPRING 2026 PREDICTION — KT.C vs DNS.C 🏆")
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
    print("  - The Effort Factor: Effort (85) brings LCK-tier veteran leadership to the Challengers roster. His shot-calling is projected to give KT.C a significant macro advantage in late-game objective setups.")
    print("  - Jungle Delta: Sylvie (82) has prior LCK experience, giving him a slight edge over DDoiV (80) in pathing efficiency and early-game map pressure.")
    print("  - Lancer's Carry Potential: Lancer (82) is the primary threat for DN SOOPers. If he can neutralize Sero (81) and snowball the top side, DNS.C has a strong path to victory.")
    print("  - Prediction: KT Rolster Challengers are favored due to their veteran experience in the jungle and support positions.")
    print("═"*72 + "\n")

if __name__ == "__main__":
    predict_dns_kt_challengers()
