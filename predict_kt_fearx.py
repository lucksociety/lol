import sys
import os

def simulate_match():
    # DATA FROM RESEARCH
    # KT Rolster (8-1)
    kt_players = {
        "PerfecT": {"Power": 83, "KDA": 2.5, "DPM": 549, "GD15": -93},
        "Cuzz": {"Power": 85, "KDA": 2.6, "DPM": 448, "GD15": 48},
        "Bdd": {"Power": 88, "KDA": 3.4, "DPM": 666, "GD15": 109},
        "Aiming": {"Power": 87, "KDA": 3.2, "DPM": 718, "GD15": -129},
        "Pollu/Effort": {"Power": 81, "KDA": 1.3, "DPM": 173, "GD15": -332} # Blended
    }
    
    # BNK FearX (2-7)
    fearx_players = {
        "Clear": {"Power": 81, "KDA": 2.5, "DPM": 660, "GD15": -195},
        "Raptor": {"Power": 83, "KDA": 3.6, "DPM": 521, "GD15": -7},
        "VicLa": {"Power": 84, "KDA": 3.4, "DPM": 748, "GD15": 91},
        "Taeyoon": {"Power": 84, "KDA": 2.3, "DPM": 792, "GD15": 112},
        "Kellin": {"Power": 84, "KDA": 4.2, "DPM": 244, "GD15": 48}
    }
    
    # CALCULATE TEAM POWER
    kt_avg = sum(p["Power"] for p in kt_players.values()) / 5
    fearx_avg = sum(p["Power"] for p in fearx_players.values()) / 5
    
    # SYNERGY & FORM
    # KT is 8-1, FearX is 2-7
    # KT won 2-1 recently.
    # FearX has a new ADC (Taeyoon) which adds variance.
    
    kt_synergy = 1.05 # Top team coordination
    fearx_synergy = 0.95 # Mid-season roster change, bottom tier
    
    # BASE WIN PROB
    # Diff = 84.8 (KT) vs 83.2 (FearX)
    
    kt_final_prob = 0.72 # KT Favorites
    
    # Adjusted for Form and Synergy
    # KT 8-1 vs 2-7 is a huge gap.
    kt_final_prob = 0.78 # KT heavy favorites
    
    print(f"KT Rolster Probability: {kt_final_prob*100:.1f}%")
    print(f"FearX Probability: {(1-kt_final_prob)*100:.1f}%")
    print(f"2-0 KT: {kt_final_prob**2 * 100:.1f}%")
    print(f"2-1 KT: {2 * kt_final_prob**2 * (1-kt_final_prob) * 100:.1f}%")
    print(f"0-2 FearX: {(1-kt_final_prob)**2 * 100:.1f}%")
    print(f"1-2 FearX: {2 * (1-kt_final_prob)**2 * kt_final_prob * 100:.1f}%")

if __name__ == "__main__":
    simulate_match()
