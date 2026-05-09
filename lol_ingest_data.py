#!/usr/bin/env python3
import os
import sys

def main():
    print("Starting Data Ingestion for LoL...")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Run the automated Leaguepedia scraper for LCK & EWC
    try:
        print("\n── 1. Fetching LCK Data ──")
        os.system(f"cd {base_dir} && python3 -m models.player_ratings compute --league LCK --split '2026 Spring'")
        
        print("\n── 2. Fetching LCK Challengers Data ──")
        os.system(f"cd {base_dir} && python3 -m models.player_ratings compute --league LCKCL --split '2026 Spring'")
        
        print("\n── 3. Fetching EWC Korea Qualifier Data ──")
        os.system(f"cd {base_dir} && python3 -m models.player_ratings compute --league EWC --split '2026 Korea Qualifier'")
        
        print("\n✅ Auto-Ingestion complete! All player powers and synergies updated in computed_ratings.json.")
        
    except Exception as e:
        print(f"Failed to run auto-scraper: {e}")
        
if __name__ == '__main__':
    main()
