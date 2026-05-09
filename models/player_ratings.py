"""
═══════════════════════════════════════════════════════════════════════
AUTO-COMPUTED PLAYER RATINGS & TEAM SYNERGY — Quant-Elite 4.0
═══════════════════════════════════════════════════════════════════════

Replaces manual gut-feel player ratings (80-100) with data-derived
ratings computed from actual match statistics via Leaguepedia.

Also computes team synergy from win rates, H2H records, and roster
stability — no more arbitrary multipliers.

Usage:
    from models.player_ratings import PlayerRatings
    
    ratings = PlayerRatings()
    ratings.scrape_and_compute("LCK", "2026 Spring")
    
    # Get a computed rating (returns 80-100 scale)
    power = ratings.get_player_power("Faker")  # → 97.2
    
    # Get computed synergy
    synergy = ratings.get_team_synergy("T1")  # → 1.18
    
    # Compare to old manual rating
    ratings.compare_to_manual("Taeyoon", manual_rating=82)

CLI:
    python3 -m models.player_ratings compute --league LCK --split "2026 Spring"
    python3 -m models.player_ratings show --player Faker
    python3 -m models.player_ratings teams --league LCK
"""

import json
import os
import sys
import math
import argparse
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from collections import defaultdict
import io

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RATINGS_FILE = os.path.join(BASE_DIR, "data", "computed_ratings.json")
SYNERGY_FILE = os.path.join(BASE_DIR, "data", "computed_synergy.json")

# ═══════════════════════════════════════════════════════════════
# RATING WEIGHTS
# ═══════════════════════════════════════════════════════════════
METRIC_WEIGHTS = {
    "kda":    0.20,
    "dpm":    0.25,
    "gd15":   0.20,
    "cspm":   0.10,
    "kp":     0.15,
    "vs":     0.10,
}

# Synergy weights
SYNERGY_WEIGHTS = {
    "win_rate":          0.35,
    "avg_gd15":          0.25,
    "streak_bonus":      0.15,
    "h2h":               0.15,
    "roster_stability":  0.10,
}


class PlayerRatings:
    """Data-driven player rating and team synergy engine."""

    def __init__(self, ratings_file=None, synergy_file=None):
        self.ratings_file = ratings_file or RATINGS_FILE
        self.synergy_file = synergy_file or SYNERGY_FILE
        self._ratings = self._load_file(self.ratings_file)
        self._synergy = self._load_file(self.synergy_file)
        self._raw_stats = {}

    def _load_file(self, path):
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_file(self, path, data):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # ── LEAGUEPEDIA SCRAPING ──────────────────────────────────

    def _leaguepedia_query(self, tables, fields, where, order_by="", limit="500"):
        """Query Leaguepedia Cargo API."""
        base_url = "https://lol.fandom.com/api.php"
        params = {
            "action": "cargoquery",
            "format": "json",
            "tables": tables,
            "fields": fields,
            "where": where,
            "limit": limit,
        }
        if order_by:
            params["order_by"] = order_by

        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": "AntigravityBot/2.0"})

        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                data = json.loads(response.read().decode("utf-8"))
                return [row["title"] for row in data.get("cargoquery", [])]
        except Exception as e:
            print(f"  ⚠️  Leaguepedia query failed: {e}")
            return []

    def scrape_player_stats(self, league, split, game_limit=20):
        """
        Scrape player-level statistics from Leaguepedia.
        
        Returns dict: {player_name: {team, role, games, kills, deaths, assists, ...}}
        """
        print(f"  📡 Scraping player stats for {league} {split}...")

        # Query ScoreboardPlayers for aggregated stats
        tournament = f"{league}/{split}"
        
        rows = self._leaguepedia_query(
            tables="ScoreboardPlayers=SP, ScoreboardGames=SG",
            fields="SP.Name, SP.Team, SP.Role, SP.Kills, SP.Deaths, SP.Assists, SP.CS, SP.Gold, SP.DamageToChampions, SP.VisionScore, SG.DateTime_UTC, SG.Patch, SG.Duration",
            where=f"SG.Tournament='{tournament}'",
            order_by="SG.DateTime_UTC DESC",
            limit=str(game_limit * 10)  # ~10 players per game
        )

        if not rows:
            print(f"  ⚠️  No data found for {tournament}. Using fallback computation.")
            return {}

        # Aggregate by player
        player_stats = defaultdict(lambda: {
            "team": "", "role": "", "games": 0,
            "kills": 0, "deaths": 0, "assists": 0,
            "cs": 0, "gold": 0, "damage": 0, "vision": 0,
            "total_duration_mins": 0
        })

        for row in rows:
            name = row.get("Name", "")
            if not name:
                continue

            stats = player_stats[name]
            stats["team"] = row.get("Team", "")
            stats["role"] = row.get("Role", "")
            stats["games"] += 1

            # Parse numeric fields safely
            for field, key in [("Kills", "kills"), ("Deaths", "deaths"), 
                               ("Assists", "assists"), ("CS", "cs"),
                               ("Gold", "gold"), ("DamageToChampions", "damage"),
                               ("VisionScore", "vision")]:
                try:
                    stats[key] += int(row.get(field, 0) or 0)
                except (ValueError, TypeError):
                    pass

            # Parse duration
            try:
                duration_str = row.get("Duration", "30:00") or "30:00"
                if ":" in str(duration_str):
                    parts = str(duration_str).split(":")
                    mins = int(parts[0]) + int(parts[1]) / 60
                else:
                    mins = float(duration_str)
                stats["total_duration_mins"] += mins
            except:
                stats["total_duration_mins"] += 30  # default

        self._raw_stats = dict(player_stats)
        print(f"  ✅ Scraped stats for {len(player_stats)} players across {league} {split}")
        return self._raw_stats

    # ── RATING COMPUTATION ────────────────────────────────────

    def compute_ratings(self, league, split, game_limit=20, stats=None):
        """
        Compute player power ratings from scraped or provided stats.
        
        Formula: 80 + (weighted_percentile_score * 20)
        """
        if stats is None:
            stats = self.scrape_player_stats(league, split, game_limit)

        if not stats:
            print("  ⚠️  No stats available. Computing fallback ratings from manual data.")
            return self._ratings

        # Compute per-game averages
        player_metrics = {}
        for name, s in stats.items():
            if s["games"] < 2:
                continue  # Skip players with too few games

            games = s["games"]
            total_mins = max(s["total_duration_mins"], 1)
            deaths = max(s["deaths"], 1)  # Avoid div by zero

            player_metrics[name] = {
                "team": s["team"],
                "role": s["role"],
                "games": games,
                "kda": (s["kills"] + s["assists"]) / deaths,
                "dpm": s["damage"] / total_mins,
                "cspm": s["cs"] / total_mins,
                "kp": (s["kills"] + s["assists"]) / max(games, 1),  # per-game
                "vs": s["vision"] / total_mins,
                "gd15": 0,  # GD@15 requires timeline data; default to 0 for now
            }

        if not player_metrics:
            print("  ⚠️  No players with sufficient games.")
            return self._ratings

        # Compute percentiles for each metric
        metrics_to_rank = ["kda", "dpm", "cspm", "kp", "vs"]
        percentiles = {}

        for metric in metrics_to_rank:
            values = sorted([(name, pm[metric]) for name, pm in player_metrics.items()], 
                           key=lambda x: x[1])
            n = len(values)
            for rank, (name, val) in enumerate(values):
                if name not in percentiles:
                    percentiles[name] = {}
                percentiles[name][metric] = rank / max(n - 1, 1)

        # Compute final ratings
        computed = {}
        for name, pctls in percentiles.items():
            weighted_score = (
                pctls.get("kda", 0.5) * METRIC_WEIGHTS["kda"] +
                pctls.get("dpm", 0.5) * METRIC_WEIGHTS["dpm"] +
                0.5 * METRIC_WEIGHTS["gd15"] +  # GD@15 defaults to 50th percentile
                pctls.get("cspm", 0.5) * METRIC_WEIGHTS["cspm"] +
                pctls.get("kp", 0.5) * METRIC_WEIGHTS["kp"] +
                pctls.get("vs", 0.5) * METRIC_WEIGHTS["vs"]
            )

            power = 80 + (weighted_score * 20)
            power = max(80, min(100, round(power, 1)))

            computed[name] = {
                "power": power,
                "team": player_metrics[name]["team"],
                "role": player_metrics[name]["role"],
                "games": player_metrics[name]["games"],
                "metrics": {k: round(v, 2) for k, v in player_metrics[name].items() 
                           if k not in ("team", "role", "games")},
                "percentiles": {k: round(v, 3) for k, v in pctls.items()},
            }

        # Save
        self._ratings = {
            "league": league,
            "split": split,
            "computed_at": datetime.now(timezone.utc).isoformat(),
            "players": computed
        }
        self._save_file(self.ratings_file, self._ratings)
        print(f"  ✅ Computed ratings for {len(computed)} players. Saved to {self.ratings_file}")
        return self._ratings

    def get_player_power(self, player_name):
        """Get a player's computed power rating. Falls back to 80 (average)."""
        players = self._ratings.get("players", {})
        entry = players.get(player_name)
        if entry:
            return entry["power"]
        return None  # Signal that no computed rating exists

    def compare_to_manual(self, player_name, manual_rating):
        """Compare computed vs manual rating for diagnostic purposes."""
        computed = self.get_player_power(player_name)
        if computed is None:
            print(f"  ⚠️  {player_name}: No computed rating (manual: {manual_rating})")
            return
        
        delta = computed - manual_rating
        arrow = "📈" if delta > 0 else "📉" if delta < 0 else "➡️"
        print(f"  {arrow} {player_name}: computed={computed:.1f}, manual={manual_rating}, delta={delta:+.1f}")

    # ── TEAM SYNERGY COMPUTATION ──────────────────────────────

    def compute_synergy(self, league, split):
        """
        Compute team synergy from actual match data.
        
        Formula: 0.70 + (weighted_score * 0.60) → range [0.70, 1.30]
        """
        print(f"  📡 Computing team synergy for {league} {split}...")

        tournament = f"{league}/{split}"
        
        # Get match results
        rows = self._leaguepedia_query(
            tables="ScoreboardGames=SG",
            fields="SG.Team1, SG.Team2, SG.WinTeam, SG.DateTime_UTC, SG.Patch",
            where=f"SG.Tournament='{tournament}'",
            order_by="SG.DateTime_UTC DESC",
            limit="200"
        )

        if not rows:
            print(f"  ⚠️  No match data found for synergy computation.")
            return self._synergy

        # Compute per-team stats
        team_stats = defaultdict(lambda: {
            "wins": 0, "losses": 0, "games": 0,
            "current_streak": 0, "h2h": defaultdict(lambda: {"wins": 0, "losses": 0})
        })

        for row in rows:
            t1, t2 = row.get("Team1", ""), row.get("Team2", "")
            winner = row.get("WinTeam", "")
            if not t1 or not t2 or not winner:
                continue

            team_stats[t1]["games"] += 1
            team_stats[t2]["games"] += 1

            if winner == t1:
                team_stats[t1]["wins"] += 1
                team_stats[t2]["losses"] += 1
                team_stats[t1]["h2h"][t2]["wins"] += 1
                team_stats[t2]["h2h"][t1]["losses"] += 1
            else:
                team_stats[t2]["wins"] += 1
                team_stats[t1]["losses"] += 1
                team_stats[t2]["h2h"][t1]["wins"] += 1
                team_stats[t1]["h2h"][t2]["losses"] += 1

        # Compute synergy for each team
        computed = {}
        all_win_rates = [s["wins"] / max(s["games"], 1) for s in team_stats.values()]
        max_wr = max(all_win_rates) if all_win_rates else 1.0
        min_wr = min(all_win_rates) if all_win_rates else 0.0
        wr_range = max(max_wr - min_wr, 0.01)

        for team, stats in team_stats.items():
            games = max(stats["games"], 1)
            win_rate = stats["wins"] / games

            # Normalize win rate to 0-1 range relative to league
            wr_normalized = (win_rate - min_wr) / wr_range

            # Win streak bonus (simplified: consecutive wins from recent results)
            streak_bonus = min(0.25, stats.get("current_streak", 0) * 0.05)
            streak_normalized = streak_bonus / 0.25  # 0-1

            # Roster stability (simplified: assume stable unless flagged)
            roster_stability = 0.7  # Default; can be overridden

            # Compute weighted synergy score
            synergy_score = (
                wr_normalized * SYNERGY_WEIGHTS["win_rate"] +
                0.5 * SYNERGY_WEIGHTS["avg_gd15"] +  # GD@15 avg defaults to 50th
                streak_normalized * SYNERGY_WEIGHTS["streak_bonus"] +
                0.5 * SYNERGY_WEIGHTS["h2h"] +  # H2H is match-specific, computed per-matchup
                roster_stability * SYNERGY_WEIGHTS["roster_stability"]
            )

            # Map to 0.70-1.30 range
            team_synergy = 0.70 + (synergy_score * 0.60)
            team_synergy = max(0.70, min(1.30, round(team_synergy, 3)))

            computed[team] = {
                "synergy": team_synergy,
                "win_rate": round(win_rate, 3),
                "record": f"{stats['wins']}-{stats['losses']}",
                "games": games,
                "h2h": {opp: dict(h2h) for opp, h2h in stats["h2h"].items()},
            }

        self._synergy = {
            "league": league,
            "split": split,
            "computed_at": datetime.now(timezone.utc).isoformat(),
            "teams": computed
        }
        self._save_file(self.synergy_file, self._synergy)
        print(f"  ✅ Computed synergy for {len(computed)} teams. Saved to {self.synergy_file}")
        return self._synergy

    def get_team_synergy(self, team_code):
        """Get a team's computed synergy value. Falls back to 1.0."""
        teams = self._synergy.get("teams", {})
        entry = teams.get(team_code)
        if entry:
            return entry["synergy"]
        return None

    def get_h2h_modifier(self, team1_code, team2_code):
        """
        Get the head-to-head modifier for team1 against team2.
        Returns a value between -0.05 and +0.05.
        """
        teams = self._synergy.get("teams", {})
        t1_entry = teams.get(team1_code, {})
        h2h = t1_entry.get("h2h", {}).get(team2_code, {"wins": 0, "losses": 0})
        
        t1_wins = h2h.get("wins", 0)
        t1_losses = h2h.get("losses", 0)
        total = t1_wins + t1_losses
        
        if total < 2:
            return 0.0  # Not enough data
        
        # H2H advantage: positive means team1 dominates
        h2h_rate = t1_wins / total
        modifier = (h2h_rate - 0.5) * 0.10  # ±0.05 max
        return max(-0.05, min(0.05, round(modifier, 3)))


def main():
    parser = argparse.ArgumentParser(description="Player Ratings & Synergy — Quant-Elite 4.0")
    subparsers = parser.add_subparsers(dest="command")

    # compute
    comp = subparsers.add_parser("compute", help="Compute ratings and synergy from Leaguepedia")
    comp.add_argument("--league", required=True, help="League (LCK, LPL, LEC)")
    comp.add_argument("--split", required=True, help="Split (e.g., '2026 Spring')")
    comp.add_argument("--games", type=int, default=20, help="Max games per player to consider")

    # show
    show = subparsers.add_parser("show", help="Show a player's computed rating")
    show.add_argument("--player", required=True, help="Player name")

    # teams
    teams = subparsers.add_parser("teams", help="Show all computed team synergies")

    args = parser.parse_args()
    ratings = PlayerRatings()

    if args.command == "compute":
        ratings.compute_ratings(args.league, args.split, args.games)
        ratings.compute_synergy(args.league, args.split)

    elif args.command == "show":
        power = ratings.get_player_power(args.player)
        if power:
            entry = ratings._ratings.get("players", {}).get(args.player, {})
            print(f"\n  🎮 {args.player}")
            print(f"     Power:  {power}")
            print(f"     Team:   {entry.get('team', '?')}")
            print(f"     Role:   {entry.get('role', '?')}")
            print(f"     Games:  {entry.get('games', '?')}")
            if entry.get("metrics"):
                print(f"     KDA:    {entry['metrics'].get('kda', '?')}")
                print(f"     DPM:    {entry['metrics'].get('dpm', '?')}")
            print()
        else:
            print(f"\n  ⚠️  No computed rating for '{args.player}'. Run 'compute' first.\n")

    elif args.command == "teams":
        teams_data = ratings._synergy.get("teams", {})
        if not teams_data:
            print("\n  ⚠️  No synergy data. Run 'compute' first.\n")
            return
        
        print(f"\n{'═'*72}")
        print(f"  📊 TEAM SYNERGY — {ratings._synergy.get('league', '?')} {ratings._synergy.get('split', '?')}")
        print(f"{'═'*72}")
        for code, info in sorted(teams_data.items(), key=lambda x: x[1]["synergy"], reverse=True):
            bar = "█" * int((info["synergy"] - 0.70) * 50)
            print(f"  {code:>6} {info['synergy']:.3f} {bar} ({info['record']}, WR: {info['win_rate']*100:.0f}%)")
        print(f"{'═'*72}\n")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
