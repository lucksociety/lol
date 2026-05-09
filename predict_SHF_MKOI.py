from models.deterministic_lol import DeterministicLoL
from datetime import datetime

def run_simulation():
    # Initialize Engine
    engine = DeterministicLoL()
    
    # ── PHASE 1: LOAD RESEARCHED 2026 DATA ───────────────────
    
    # Update Player Power with Researched Values
    engine.player_power.update({
        # Shifters (SHF)
        "Rooster": 82,
        "Sheo": 84,
        "nuc": 83,
        "Paduck": 84,
        "Trymbi": 85,
        
        # Movistar KOI (MKOI)
        "Myrwn": 86,
        "Elyoya": 90,
        "Jojopyun": 91,
        "Supa": 89,
        "Alvaro": 87
    })
    
    # Update Team Synergy
    engine.team_synergy.update({
        "SHF": 0.98,  # Recent jungle swap (Sheo), though improving
        "MKOI": 1.05  # High stability, veteran core
    })
    
    # ── PHASE 2: CONSTRUCT MATCH DATA ────────────────────────
    
    team1 = {
        "name": "SHF",
        "league": None,
        "roster": ["Rooster", "Sheo", "nuc", "Paduck", "Trymbi"],
        "gd15_trend": 50, # Beating Heretics showed positive trend
        "roster_change": True, # Sheo joined April 27
        "patch_games": 6,
        "h2h_modifier": 0.02, # Won Bo1 in January
        "aggression_variance": 0.12 # High variance team
    }
    
    team2 = {
        "name": "MKOI",
        "league": None,
        "roster": ["Myrwn", "Elyoya", "Jojopyun", "Supa", "Alvaro"],
        "gd15_trend": 84,
        "patch_games": 8,
        "h2h_modifier": -0.02,
        "aggression_variance": 0.05 # Disciplined elite team
    }
    
    # Market Intelligence (Official Odds)
    market_odds = {
        "SHF ML": 228,
        "MKOI ML": -333,
        "SHF +1.5": -118,
        "MKOI -1.5": -111,
        "Over 2.5 Maps": 138,
        "Under 2.5 Maps": -185
    }
    
    # ── PHASE 3: EXECUTE SIMULATION ───────────────────────────
    print(f"\nACTIVATING LOL OMNI-PROPHET V5.0 ENGINE...")
    print(f"Match: Shifters (SHF) vs Movistar KOI (MKOI)")
    print(f"Format: Best of 3 | Iterations: 100,000\n")
    
    results = engine.simulate_bo3(
        team1, 
        team2, 
        iterations=100000,
        market_odds=market_odds
    )
    
    # The engine automatically prints the Forensic Report as per its source code.

if __name__ == "__main__":
    run_simulation()
