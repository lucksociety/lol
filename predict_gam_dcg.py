import math
import random
import sys
import os

# Ensure the models directory is in the path
sys.path.append(os.getcwd())
from models.deterministic_lol import DeterministicLoL

def run_gam_dcg_prediction():
    model = DeterministicLoL()
    
    # Update player power for the 2026 LCP rosters based on Intelligence Report
    # Scale: 80 (Average) - 100 (God-Tier)
    # GAM Rating: 8.4 (A Tier)
    # DCG Rating: 6.8 (C Tier)
    model.player_power.update({
        # GAM Esports (GAM)
        "Kiaya": 88,      # Top-tier threat, veteran presence
        "Draktharr": 83,
        "Aress": 86,      # Standout performance (5.65 KDA)
        "Artemis": 85,    # Reliable ADC (Yunara specialist)
        "Taki": 84,
        
        # Deep Cross Gaming (DCG)
        "Flauren": 79,
        "POP9": 80,
        "HongSuo": 82,    # Reliable mid (3.34 KDA)
        "Feng": 77,       # Struggling bot lane (2.36 KDA)
        "ShiauC": 81      # Experienced support
    })
    
    # Set synergy based on recent developments
    # GAM is "The Chaos Engine" with high FB% but some BO3 consistency issues.
    # DCG is a "Regression Candidate" who lost their identity in Split 2.
    model.team_synergy["GAM"] = 1.08  # High pressure style
    model.team_synergy["DCG"] = 0.82  # Identity crisis, negative GD@15
    
    match = {
        "team1": {
            "name": "GAM",
            "tier": "A",
            "roster": ["Kiaya", "Draktharr", "Aress", "Artemis", "Taki"],
            "aggression_variance": 0.22  # High chaos engine weight
        },
        "team2": {
            "name": "DCG",
            "tier": "C",
            "roster": ["Flauren", "POP9", "HongSuo", "Feng", "ShiauC"],
            "aggression_variance": 0.05  # Low proactive play
        }
    }
    
    # Run Bo3 Simulation (100k iterations)
    res = model.simulate_bo3(match["team1"], match["team2"])
    
    print("\n" + "═"*72)
    print("  🏆 LCP SPLIT 2 2026 PREDICTION — GAM vs DEEP CROSS GAMING 🏆")
    print("              MAY 2, 2026")
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
    print("  - The Chaos Engine vs Identity Crisis: GAM boasts the league's highest First Blood rate (70%), which directly exploits DCG's weak early game (-283 GD@15).")
    print("  - Bot Lane Mismatch: Artemis (GAM) has been elite on Yunara, while Feng (DCG) is currently the weakest-performing ADC in the LCP (2.36 KDA). Expect heavy pressure on the bottom side.")
    print("  - Macro Delta: GAM's objective control (60% Baron) is significantly more refined than DCG's reactive playstyle. Even if games start slow, GAM's mid-game pace usually forces errors.")
    print("  - Verdict: GAM is a heavy favorite. DCG's regression in Split 2 makes them a high-risk underdog with very little win-condition outside of a HongSuo miracle.")
    print("  - Recommendation: GAM -1.5 Spread. The mismatch in bot lane and jungle pressure suggests a clean 2-0 sweep is the most probable outcome.")
    print("═"*72 + "\n")

if __name__ == "__main__":
    run_gam_dcg_prediction()
