import os
import sys
from datetime import datetime

# Add the project root to sys.path
sys.path.insert(0, '/Users/danielreiss/Desktop/Antigravity/LoL')

from models.deterministic_lol import DeterministicLoL

def run_simulation():
    engine = DeterministicLoL()
    
    # Update Player Power with RESEARCHED 2026 values
    # Based on KDA, DPM, and recent form
    engine.player_power.update({
        # Dplus KIA
        "Siwoo": 85,
        "Lucid": 87,
        "ShowMaker": 90,
        "Smash": 89,
        "Career": 86,
        
        # NS RedForce
        "Kingen": 86,
        "Sponge": 84,
        "Scout": 91,
        "Diable": 83,
        "Lehends": 88
    })
    
    # Set Team Synergy based on 2026 Spring record and recent form
    engine.team_synergy.update({
        "DK": 1.05,  # 14-9 record, stable
        "NS": 0.98   # 9-13 record, but recent roster shift (Diable)
    })
    
    # Define Matchup Data
    team1 = {
        "name": "DK",
        "league": "LCK",
        "roster": ["Siwoo", "Lucid", "ShowMaker", "Smash", "Career"],
        "side": "blue",          # Game 1 side selection (higher seed)
        "patch_games": 2,        # Games on Patch 16.9
        "h2h_modifier": -0.02,   # Struggle in last H2H (lost 0-2)
        "unique_champions": 44,  # Combined team pool
        "gd15_trend": 28,        # Positive gold trend
        "tier": "A"
    }
    
    team2 = {
        "name": "NS",
        "league": "LCK",
        "roster": ["Kingen", "Sponge", "Scout", "Diable", "Lehends"],
        "side": "red",
        "patch_games": 2,
        "h2h_modifier": 0.02,    # Recent 2-0 victory over DK
        "unique_champions": 42,
        "gd15_trend": -15,       # Slightly negative trend due to Diable transition
        "tier": "B"
    }
    
    # Market Odds (from Phase 1.5 Research)
    market_odds = {
        "DK ML": -280,   # ~1.36
        "NS ML": +210,   # ~3.10
        "DK -1.5": +115, # Spread
        "NS +1.5": -145  # Spread
    }
    
    # Run Simulation (100,000 iterations)
    result = engine.simulate_bo3(
        team1, 
        team2, 
        iterations=100000, 
        require_verification=True,
        market_odds=market_odds
    )
    
    return result

if __name__ == "__main__":
    run_simulation()
