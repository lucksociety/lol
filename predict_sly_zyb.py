import math
import random
import sys
import os

# Import the DeterministicLoL engine from the workspace
sys.path.append("/Users/danielreiss/Desktop/Antigravity/LoL")
from models.deterministic_lol import DeterministicLoL

def predict_sly_zyb():
    model = DeterministicLoL()
    
    # Update player power for the LFL Spring rosters
    model.player_power.update({
        # Solary (SLY)
        "Kryze": 86,
        "Zicssi": 88,
        "Jool": 84,
        "Aetinoth": 83,
        "Piero": 82,
        
        # Zyb Esport (ZYB)
        "Wao": 82,
        "Manaty": 83,
        "Nisqy": 90,
        "Jezu": 86,
        "Riippp": 80
    })
    
    # Set synergy based on current form (Solary 7-1, Zyb 2-5)
    model.team_synergy["Solary"] = 1.40  # Reigning EMEA Masters Champs + 7-1 momentum
    model.team_synergy["Zyb Esport"] = 0.85  # Struggling to find rhythm despite star power
    
    match = {
        "team1": {
            "name": "Solary",
            "roster": ["Kryze", "Zicssi", "Jool", "Aetinoth", "Piero"],
            "tier": "A+"
        },
        "team2": {
            "name": "Zyb Esport",
            "roster": ["Wao", "Manaty", "Nisqy", "Jezu", "Riippp"],
            "tier": "B"
        }
    }
    
    # Calculate Bo1 Probability
    win_prob = model.calculate_match_probability(match["team1"], match["team2"])
    
    print("\n" + "═"*72)
    print("  🏆 LFL SPRING PREDICTION — SOLARY vs ZYB ESPORT 🏆")
    print("              MAY 1, 2026 - 4:00 PM")
    print("═"*72)
    
    print(f"\n  MATCHUP: {match['team1']['name']} vs {match['team2']['name']}")
    print(f"  Win Probability: {win_prob*100:.1f}% ({match['team1']['name']})")
    print(f"  Implied Odds (Decimal): {1/win_prob:.2f}")
    print(f"  Implied Odds (American): -{int((win_prob/(1-win_prob))*100)}")
    
    print("\n  ROSTER COMPARISON:")
    for i, role in enumerate(["TOP", "JNG", "MID", "ADC", "SUP"]):
        p1 = match['team1']['roster'][i]
        p2 = match['team2']['roster'][i]
        pow1 = model.player_power[p1]
        pow2 = model.player_power[p2]
        diff = pow1 - pow2
        sign = "+" if diff >= 0 else ""
        print(f"    {role:<4}: {p1:<10} ({pow1}) vs {p2:<10} ({pow2}) | Delta: {sign}{diff}")

    print("\n" + "═"*72)
    print("  STRATEGIC INSIGHTS:")
    print("  - Roster Disparity: ZYB boasts superior individual peaks in Nisqy (90) and Jezu (86). On paper, their mid-lane talent should dominate.")
    print("  - The Synergy Chasm: Solary's 1.40 synergy (reigning EMEA Masters champs) vs ZYB's 0.85 (bottom-tier performance) is the deciding factor. Solary plays as a unit; ZYB plays as five individuals.")
    print("  - Jungle Control: Zicssi (88) has been the MVP of the LFL so far. Expect him to neutralize Manaty and shadow Nisqy to prevent a ZYB snowball.")
    print("  - Prediction: Solary's discipline and macro superiority will overwhelm ZYB's raw but disjointed talent. A clean win for the league leaders.")
    print("═"*72 + "\n")

if __name__ == "__main__":
    predict_sly_zyb()
