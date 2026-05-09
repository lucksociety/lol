#!/usr/bin/env python3
import argparse
import sys
import os
import json
from datetime import datetime
import io

# Import the existing DeterministicLoL engine
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from models.deterministic_lol import DeterministicLoL

def update_computed_ratings(filepath, overrides):
    """Inject missing player ratings into computed_ratings.json."""
    if not os.path.exists(filepath):
        return
        
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    players = data.get("players", {})
    changed = False
    
    for override in overrides:
        # Format: Name:Power:Team:Role:Games
        parts = override.split(":")
        if len(parts) >= 5:
            name, power, team, role, games = parts[:5]
            players[name] = {
                "power": float(power),
                "team": team,
                "role": role,
                "games": int(games),
                "metrics": {},
                "percentiles": {}
            }
            changed = True
            
    if changed:
        data["players"] = players
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

def main():
    parser = argparse.ArgumentParser(description="LoL Auto Sim V5 Wrapper")
    parser.add_argument("--team1", required=True)
    parser.add_argument("--team2", required=True)
    parser.add_argument("--team1_roster", required=True, help="Comma separated list of 5 players")
    parser.add_argument("--team2_roster", required=True, help="Comma separated list of 5 players")
    
    # Optional Modifiers
    parser.add_argument("--league", default="LCK")
    parser.add_argument("--team1_odds", type=int, default=0)
    parser.add_argument("--team2_odds", type=int, default=0)

    # Smart Orchestration Flags
    parser.add_argument("--check_data", action="store_true", help="Pre-flight check only. Returns JSON.")
    parser.add_argument("--override_player", action="append", default=[], help="Format: 'Name:Power:Team:Role:Games'")
    parser.add_argument("--save_overrides", action="store_true", help="Permanently save overrides to JSON")
    parser.add_argument("--market_surge", type=float, default=0.0, help="Market volume shift toward Team 2 (e.g., 26.0 for a 26% surge toward underdog)")

    args = parser.parse_args()
    
    ratings_file = os.path.join(os.path.dirname(__file__), "data", "computed_ratings.json")

    # 1. Handle Overrides & Auto-Caching
    if args.override_player and args.save_overrides:
        try:
            update_computed_ratings(ratings_file, args.override_player)
        except Exception as e:
            print(f"Failed to update overrides: {e}", file=sys.stderr)

    # 2. Check Data
    sim = DeterministicLoL()
    
    team1_roster = [n.strip() for n in args.team1_roster.split(',')]
    team2_roster = [n.strip() for n in args.team2_roster.split(',')]
    
    missing_players = []
    
    for roster in [team1_roster, team2_roster]:
        for player in roster:
            if sim._get_player_power(player) == 80: # 80 is the default fallback if missing
                # Double check it actually doesn't exist in the JSON or manual dict
                players_json = sim._ratings_engine._ratings.get("players", {}) if sim._using_computed_ratings else {}
                if player not in players_json and player not in sim.player_power:
                    missing_players.append(f"PLAYER:{player}")

    if args.check_data:
        if missing_players:
            print(json.dumps({"status": "STALE_OR_MISSING", "missing": missing_players}))
        else:
            print(json.dumps({"status": "OK", "missing": []}))
        sys.exit(0)

    # 3. Build teams and run simulation
    team1 = {
        "name": args.team1,
        "league": args.league,
        "roster": team1_roster
    }
    
    team2 = {
        "name": args.team2,
        "league": args.league,
        "roster": team2_roster
    }
    
    market_odds = {}
    if args.team1_odds != 0:
        market_odds[f"{args.team1} ML"] = args.team1_odds
    if args.team2_odds != 0:
        market_odds[f"{args.team2} ML"] = args.team2_odds
        
    try:
        # Require verification = False so it doesn't hard-fail if not in verified_rosters.json
        sim.simulate_bo3(team1, team2, iterations=100000, market_odds=market_odds, require_verification=False, market_surge=args.market_surge)
    except Exception as e:
        print(f"SIMULATION FAILED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
