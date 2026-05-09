import math
import random
import sys
import os

# Import the DeterministicLoL engine from the workspace
sys.path.append("/Users/danielreiss/Desktop/Antigravity/LoL")
from models.deterministic_lol import DeterministicLoL

def predict_hle_t1_lck():
    model = DeterministicLoL()
    
    # Update player power for the LCK 2026 rosters
    model.player_power.update({
        # T1 (The Resurgent)
        "Doran": 88,
        "Oner": 90,
        "Faker": 96,
        "Peyz": 94,
        "Keria": 95,
        
        # HLE (The Superteam)
        "Zeus": 98,
        "Kanavi": 94,
        "Zeka": 92,
        "Gumayusi": 96,
        "Delight": 93
    })
    
    # Set synergy based on current win streaks and H2H history
    model.team_synergy["T1"] = 1.15   # Faker/Keria synergy is constant
    model.team_synergy["HLE"] = 1.25  # Superteam clicking (7-match win streak)
    
    match = {
        "team1": {
            "name": "Hanwha Life Esports",
            "roster": ["Zeus", "Kanavi", "Zeka", "Gumayusi", "Delight"],
            "tier": "S"
        },
        "team2": {
            "name": "T1",
            "roster": ["Doran", "Oner", "Faker", "Peyz", "Keria"],
            "tier": "S"
        }
    }
    
    # Run Bo3 Simulation (100k iterations)
    res = model.simulate_bo3(match["team1"], match["team2"])
    
    print("\n" + "═"*72)
    print("  🏆 LCK SPRING 2026 PREDICTION — HLE vs T1 🏆")
    print("              MAY 1, 2026 - 6:00 AM")
    print("═"*72)
    
    print(f"\n  MATCHUP: {match['team1']['name']} vs {match['team2']['name']}")
    print(f"  Series Win Prob: {res['win_prob']*100:.1f}% ({match['team1']['name']})")
    print(f"  Base Game Prob: {res['base_game_prob']*100:.1f}%")
    print(f"  Likely Scores:")
    # Sort scores
    sorted_scores = sorted(res["scores"].items(), key=lambda x: x[1], reverse=True)
    for score, prob in sorted_scores:
        bar = "█" * int(prob * 20)
        print(f"    {score}: {prob*100:>5.1f}% {bar}")
            
    print("\n" + "═"*72)
    print("  STRATEGIC INSIGHTS:")
    print("  - The Zeus Gap: Zeus (98) remains the premier top laner in the world. While Doran (88) is consistent, the matchup favors HLE's ability to create a massive top-side advantage early.")
    print("  - Macro Coordination: T1 handed HLE their only loss of the split on April 4th. Faker's late-game shotcalling remains the one weapon HLE's superteam hasn't fully mastered.")
    print("  - Revenge Narrative: Zeus and Gumayusi facing their former org with the #1 seed on the line. Psychological pressure favors HLE's 'win-now' roster.")
    print("  - Prediction: HLE's 7-match momentum and raw individual power (Avg: 94.6 vs T1's 92.6) make them the statistical favorites for a 2-1 victory.")
    print("═"*72 + "\n")

if __name__ == "__main__":
    predict_hle_t1_lck()
