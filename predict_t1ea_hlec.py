import math
import random
import sys
import os

sys.path.append(os.getcwd())
from models.deterministic_lol import DeterministicLoL

def run_t1ea_hlec_prediction():
    model = DeterministicLoL()
    
    model.player_power.update({
        # T1 Esports Academy
        "Haetae": 88,
        "Painter": 86,
        "Guti": 89,
        "Cypher": 87,
        "Cloud": 88,
        
        # Hanwha Life Esports Challengers
        "Panther": 86,
        "Jackal": 85,
        "Cracker": 87,
        "Pyeonsik": 86,
        "Bluffing": 85
    })
    
    model.team_synergy["T1.EA"] = 1.10  # Exceptional macro, top 2 team
    model.team_synergy["HLE.C"] = 1.02  # Standard
    
    match = {
        "team1": {
            "name": "T1.EA",
            "roster": ["Haetae", "Painter", "Guti", "Cypher", "Cloud"],
            "aggression_variance": 0.05
        },
        "team2": {
            "name": "HLE.C",
            "roster": ["Panther", "Jackal", "Cracker", "Pyeonsik", "Bluffing"],
            "aggression_variance": 0.10
        }
    }
    
    res = model.simulate_bo3(match["team1"], match["team2"])
    
    print("\n" + "═"*72)
    print("  🏆 LCK CL SPRING 2026 PREDICTION — T1.EA vs HLE.C 🏆")
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
    print("  - Elite Roster Power: T1.EA has superior players in nearly every position. Guti (89) is a monster.")
    print("  - Macro Superiority: T1.EA's synergy (1.10) reflects their Kickoff tournament dominance.")
    print("  - HLE.C Context: Panther (86) is too coin-flip against a stable top laner like Haetae (88).")
    print("  - Verdict: T1.EA should dominate. High probability of a 2-0.")
    print("═"*72 + "\n")

if __name__ == "__main__":
    run_t1ea_hlec_prediction()
