import math
import random
import sys
import os

# Import the DeterministicLoL engine from the workspace
sys.path.append("/Users/danielreiss/Desktop/Antigravity/LoL")
from models.deterministic_lol import DeterministicLoL

def predict_fnc_solary():
    model = DeterministicLoL()
    
    # Update player power for the EWC Qualifier rosters
    model.player_power.update({
        # Fnatic (FNC)
        "Empyros": 87,
        "Razork": 92,
        "Vladi": 88,
        "Upset": 94,
        "Lospa": 86,
        
        # Solary (SLY)
        "Kryze": 86,
        "Zicssi": 88,
        "Jool": 84,
        "Aetinoth": 83,
        "Piero": 82
    })
    
    # Set synergy
    model.team_synergy["FNC"] = 1.15
    model.team_synergy["SLY"] = 1.40  # Massive momentum (EMEA Masters Champs)
    
    match = {
        "team1": {
            "name": "Fnatic",
            "roster": ["Empyros", "Razork", "Vladi", "Upset", "Lospa"],
            "tier": "S"
        },
        "team2": {
            "name": "Solary",
            "roster": ["Kryze", "Zicssi", "Jool", "Aetinoth", "Piero"],
            "tier": "A"
        }
    }
    
    # Run Bo3 Simulation (100k iterations)
    res = model.simulate_bo3(match["team1"], match["team2"])
    
    print("\n" + "═"*72)
    print("  🏆 EWC QUALIFIER PREDICTION — FNATIC vs SOLARY 🏆")
    print("              APRIL 30, 2026 - 2:00 PM")
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
    print("  - Mechanical Gap vs. Synergy: Fnatic boasts superior individual skill, especially in the bot lane with Upset (94). However, Solary's 1.40 synergy rating reflects their incredible coordination as the reigning EMEA Masters champions.")
    print("  - Jungle Tempo: Razork (92) vs Zicssi (88) is the most critical matchup. Razork's ability to disrupt Solary's disciplined early game is the win condition for FNC.")
    print("  - The 'David vs Goliath' Factor: Solary has already defeated multiple LEC teams in this bracket. Their confidence is at an all-time high.")
    print("  - Prediction: A coin-flip series where Fnatic's raw talent is narrowly favored to break Solary's perfect coordination.")
    print("═"*72 + "\n")

if __name__ == "__main__":
    predict_fnc_solary()
