import sys
import os
from datetime import datetime

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from models.deterministic_lol import DeterministicLoL

def run_simulation():
    model = DeterministicLoL()
    
    # PHASE 1: RESEARCHED DATA INTEGRATION (2026 Season)
    # Scale: 80 (Average) - 100 (God-Tier)
    model.player_power.update({
        # Team Vitality (VIT) - Tier S (9.5 Rating)
        "Naak Nako": 92,   # Top
        "Lyncas": 95,      # Jungle
        "Humanoid": 94,    # Mid
        "Carzzy": 96,      # ADC (DPM Leader 876)
        "Fleshy": 96,      # Support (GD15 +287)
        
        # Fnatic (FNC) - Tier C (4.5 Rating)
        "Empyros": 80,     # Top
        "Razork": 82,      # Jungle
        "Vladi": 84,       # Mid
        "Upset": 90,       # ADC (Strongest FNC asset)
        "Lospa": 81        # Support
    })
    
    model.team_synergy.update({
        "VIT": 1.05,       # 7-1 Record, 7-game win streak, elite macro
        "FNC": 0.92        # 3-5 Record, "Early Aggro Trap", negative MLR
    })
    
    # Match Context
    team_vit = {
        "name": "VIT",
        "league": "LEC",
        "tier": "S",
        "roster": ["Naak Nako", "Lyncas", "Humanoid", "Carzzy", "Fleshy"],
        "gd15_trend": 1037,
        "fb_pct": 0.72,
        "side": "blue",    # Assuming VIT picks Blue Game 1 as higher seed
        "patch_games": 8,  # Vitality played full split
        "h2h_modifier": 0.02, # 2-1 Game record in 2026 H2H
        "unique_champions": 22
    }
    
    team_fnc = {
        "name": "FNC",
        "league": "LEC",
        "tier": "C",
        "roster": ["Empyros", "Razork", "Vladi", "Upset", "Lospa"],
        "gd15_trend": -150, # "Early aggro trap" implies fading lead
        "fb_pct": 0.67,
        "side": "red",
        "patch_games": 8,
        "h2h_modifier": -0.02,
        "unique_champions": 18
    }
    
    # Market Intelligence (May 4, 11:00)
    # VIT 1.21 (-476), FNC 3.53 (+253)
    market_odds = {
        "VIT Moneyline": -233,
        "FNC Moneyline": 175,
        "VIT -1.5 Spread": 139,
        "FNC +1.5 Spread": -182
    }
    
    # Run Simulation (100,000 iterations)
    result = model.simulate_bo_series(team_vit, team_fnc, best_of=3, iterations=100000, market_odds=market_odds)
    
    return result

if __name__ == "__main__":
    run_simulation()
