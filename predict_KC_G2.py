#!/usr/bin/env python3
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.deterministic_lol import DeterministicLoL

def main():
    sim = DeterministicLoL()
    
    # Set Player Ratings (Scale 80-100)
    # Karmine Corp (6-0, Locked 2nd)
    sim.player_power["Canna"] = 93
    sim.player_power["Yike"] = 92
    sim.player_power["Kyeahoo"] = 95
    sim.player_power["Caliste"] = 98
    sim.player_power["Busio"] = 91
    
    # G2 Esports (4-2, Fighting for Top 4)
    sim.player_power["BrokenBlade"] = 88
    sim.player_power["SkewMond"] = 90
    sim.player_power["Caps"] = 97
    sim.player_power["Hans Sama"] = 94
    sim.player_power["Labrov"] = 86
    
    # Set Team Synergy
    sim.team_synergy["KC"] = 1.65 # Undefeated macro synergy
    sim.team_synergy["G2"] = 1.30 # High damage but negative GD15 historically
    
    team1 = {
        "name": "KC",
        "league": "LEC",
        "roster": ["Canna", "Yike", "Kyeahoo", "Caliste", "Busio"],
        "tier": "S",
        "h2h_modifier": -0.01, # G2 leads all-time and won recent finals
        "side": "blue" # Assuming KC has side choice as higher seed
    }
    
    team2 = {
        "name": "G2",
        "league": "LEC",
        "roster": ["BrokenBlade", "SkewMond", "Caps", "Hans Sama", "Labrov"],
        "tier": "A",
        "fatigued": False
    }
    
    # Market Surge: User mentioned context of "Locked" vs "Desperate"
    # G2 has 100% motivation, KC might limit test. 
    # Let's simulate a 15% sentiment surge toward G2 due to motivation.
    
    print("\n" + "="*72)
    print("  OMNI-PROPHET V5.0 | KC VS G2 PREGAME FORENSIC SIMULATION")
    print("  Madrid Roadtrip | May 8, 2026")
    print("="*72)
    
    # Run simulation
    market_odds = {
        "KC ML": 135,
        "G2 ML": -175,
        "KC +1.5": -225,
        "G2 -1.5": 170,
        "Over 2.5": -105,
        "Under 2.5": -125
    }
    
    sim.simulate_bo3(team1, team2, iterations=100000, market_surge=15.0, require_verification=False, market_odds=market_odds)

if __name__ == "__main__":
    main()
