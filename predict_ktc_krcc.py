import math
import random
import sys
import os

sys.path.append(os.getcwd())
from models.deterministic_lol import DeterministicLoL

def run_ktc_krcc_prediction():
    model = DeterministicLoL()
    
    model.player_power.update({
        # KT Rolster Challengers
        "Sero": 85,
        "Sylvie": 88,
        "Hwichan": 86,
        "FenRir": 85,
        "Pollu": 87,
        
        # KIWOOM DRX Challengers
        "Winner": 84,
        "Minous": 85,
        "Frog": 83,
        "AKaJe": 84,
        "Sub_Sup": 82
    })
    
    model.team_synergy["KT.C"] = 1.03  # Sylvie dictates pace effectively
    model.team_synergy["KRC.C"] = 0.98  # Identity crisis after Jiwoo call-up
    
    match = {
        "team1": {
            "name": "KT.C",
            "roster": ["Sero", "Sylvie", "Hwichan", "FenRir", "Pollu"],
            "aggression_variance": 0.08
        },
        "team2": {
            "name": "KRC.C",
            "roster": ["Winner", "Minous", "Frog", "AKaJe", "Sub_Sup"],
            "aggression_variance": 0.10
        }
    }
    
    res = model.simulate_bo3(match["team1"], match["team2"])
    
    print("\n" + "═"*72)
    print("  🏆 LCK CL SPRING 2026 PREDICTION — KT.C vs KRC.C 🏆")
    print("              MAY 4, 2026")
    print("═"*72)
    
    print(f"\n  MATCHUP: {match['team1']['name']} vs {match['team2']['name']}")
    t1_win_prob = res['win_prob']
    t2_win_prob = 1 - t1_win_prob
    
    winner = match['team1']['name'] if t1_win_prob > 0.5 else match['team2']['name']
    winner_prob = max(t1_win_prob, t2_win_prob)
    
    print(f"  Series Win Prob: {winner_prob*100:.1f}% ({winner})")
    print(f"  Base Game Prob: {res['base_game_prob']*100:.1f}%")
    print(f"  Likely Scores:")
    sorted_scores = sorted(res["scores"].items(), key=lambda x: x[1], reverse=True)
    for score, prob in sorted_scores:
        bar = "█" * int(prob * 20)
        print(f"    {score}: {prob*100:>5.1f}% {bar}")
            
    print("\n" + "═"*72)
    print("  STRATEGIC INSIGHTS:")
    print("  - Jungle Kingdom: Sylvie (88) outclasses Minous (85) significantly in early game impact.")
    print("  - Roster Impact: KRC.C's loss of Jiwoo has severely impacted their late-game insurance.")
    print("  - Value Trap Avoidance: KRC.C has losing H2H records vs top-tier teams. Flagged as a fade.")
    print("  - Verdict: KT.C is the high-conviction side here.")
    print("═"*72 + "\n")

if __name__ == "__main__":
    run_ktc_krcc_prediction()
