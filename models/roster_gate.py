"""
═══════════════════════════════════════════════════════════════════════
ROSTER VERIFICATION GATE — Quant-Elite 3.2
═══════════════════════════════════════════════════════════════════════

HARD GATE: No simulation runs without verified rosters. Period.

This module provides:
  1. A verified_rosters.json data store (single source of truth)
  2. require_verified_roster() — blocks simulation if unverified
  3. verify_roster() — confirms and timestamps a roster
  4. Staleness detection — rosters >12h old are STALE
  5. Cross-check — catches mismatches between script input and verified data

Usage in prediction scripts:
    from models.roster_gate import RosterGate
    gate = RosterGate()
    kt_roster = gate.require_verified_roster("KT")
    bro_roster = gate.require_verified_roster("BRO")
    # Only THEN proceed to simulation

CLI Usage:
    python3 -m models.roster_gate verify KT --players PerfecT Cuzz Bdd Aiming Pollu --source liquipedia
    python3 -m models.roster_gate check KT
    python3 -m models.roster_gate status
    python3 -m models.roster_gate cross-check KT PerfecT Cuzz Bdd Aiming Pollu
"""

import json
import os
import sys
import argparse
from datetime import datetime, timezone, timedelta
import io

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROSTER_FILE = os.path.join(BASE_DIR, "data", "verified_rosters.json")
STALENESS_HOURS = 12
ROLES = ["top", "jungle", "mid", "adc", "support"]


# ═══════════════════════════════════════════════════════════════
# CUSTOM EXCEPTIONS
# ═══════════════════════════════════════════════════════════════
class RosterNotVerifiedError(Exception):
    """Raised when a simulation is attempted with an unverified roster."""
    pass

class RosterStaleError(Exception):
    """Raised when a roster verification is older than STALENESS_HOURS."""
    pass

class RosterMismatchError(Exception):
    """Raised when the script's roster doesn't match the verified roster."""
    pass


# ═══════════════════════════════════════════════════════════════
# ROSTER GATE
# ═══════════════════════════════════════════════════════════════
class RosterGate:
    """Mandatory pre-simulation verification gate."""

    def __init__(self, roster_file=None):
        self.roster_file = roster_file or ROSTER_FILE
        self._rosters = self._load()

    def _load(self):
        """Load verified rosters from disk."""
        if os.path.exists(self.roster_file):
            with open(self.roster_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save(self):
        """Persist verified rosters to disk."""
        os.makedirs(os.path.dirname(self.roster_file), exist_ok=True)
        with open(self.roster_file, "w", encoding="utf-8") as f:
            json.dump(self._rosters, f, indent=2, ensure_ascii=False)

    def _now_iso(self):
        return datetime.now(timezone.utc).isoformat()

    def _is_stale(self, verified_at_str):
        """Check if a verification timestamp is older than STALENESS_HOURS."""
        try:
            verified_at = datetime.fromisoformat(verified_at_str)
            if verified_at.tzinfo is None:
                verified_at = verified_at.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            return (now - verified_at) > timedelta(hours=STALENESS_HOURS)
        except (ValueError, TypeError):
            return True  # If we can't parse the timestamp, treat as stale

    # ── PUBLIC API ────────────────────────────────────────────

    def verify_roster(self, team_code, full_name, league, players, subs=None, source="manual", verified_by="agent"):
        """
        Confirm a team's active roster. This is the ONLY way to unlock simulation.

        Args:
            team_code: Short code (e.g., "KT", "BFX")
            full_name: Full team name (e.g., "KT Rolster")
            league: League code (e.g., "LCK", "LPL")
            players: dict with keys: top, jungle, mid, adc, support
            subs: optional dict of known substitutes
            source: Where the data was confirmed (e.g., "liquipedia.net")
            verified_by: Who verified (e.g., "agent", "user")
        """
        # Validate player roles
        for role in ROLES:
            if role not in players:
                raise ValueError(f"Missing required role '{role}' in players dict. Required: {ROLES}")

        self._rosters[team_code] = {
            "full_name": full_name,
            "league": league,
            "players": players,
            "subs": subs or {},
            "verified_at": self._now_iso(),
            "source": source,
            "verified_by": verified_by
        }
        self._save()
        return self._rosters[team_code]

    def require_verified_roster(self, team_code):
        """
        HARD GATE: Returns the verified roster or raises an exception.
        This MUST be called before any simulation.

        Returns:
            dict with keys: full_name, league, players, verified_at, source

        Raises:
            RosterNotVerifiedError: if team has no verified roster
            RosterStaleError: if verification is older than 12 hours
        """
        if team_code not in self._rosters:
            raise RosterNotVerifiedError(
                f"\n{'═'*72}\n"
                f"  ❌ SIMULATION BLOCKED — ROSTER NOT VERIFIED\n"
                f"{'═'*72}\n"
                f"  Team '{team_code}' has NO verified roster.\n\n"
                f"  To fix, run:\n"
                f"    python3 -m models.roster_gate verify {team_code} \\\n"
                f"      --name 'Team Full Name' --league LCK \\\n"
                f"      --players Top Jgl Mid ADC Sup \\\n"
                f"      --source liquipedia\n"
                f"{'═'*72}\n"
            )

        entry = self._rosters[team_code]

        if self._is_stale(entry.get("verified_at", "")):
            hours_ago = "unknown"
            try:
                verified_at = datetime.fromisoformat(entry["verified_at"])
                if verified_at.tzinfo is None:
                    verified_at = verified_at.replace(tzinfo=timezone.utc)
                hours_ago = f"{(datetime.now(timezone.utc) - verified_at).total_seconds() / 3600:.1f}h"
            except:
                pass

            raise RosterStaleError(
                f"\n{'═'*72}\n"
                f"  ⚠️  SIMULATION BLOCKED — ROSTER IS STALE\n"
                f"{'═'*72}\n"
                f"  Team '{team_code}' roster was verified {hours_ago} ago.\n"
                f"  Maximum allowed: {STALENESS_HOURS}h.\n"
                f"  Current roster: {list(entry['players'].values())}\n"
                f"  Source: {entry.get('source', 'unknown')}\n\n"
                f"  To re-verify, run:\n"
                f"    python3 -m models.roster_gate verify {team_code} \\\n"
                f"      --players Top Jgl Mid ADC Sup --source liquipedia\n"
                f"{'═'*72}\n"
            )

        return entry

    def cross_check_roster(self, team_code, script_roster):
        """
        Cross-check that a prediction script's roster matches the verified data.

        Args:
            team_code: Team code
            script_roster: list of 5 player names [Top, Jgl, Mid, ADC, Sup]

        Raises:
            RosterMismatchError: if any player doesn't match
        """
        entry = self.require_verified_roster(team_code)
        verified_players = entry["players"]

        mismatches = []
        for i, role in enumerate(ROLES):
            verified_player = verified_players[role]
            script_player = script_roster[i] if i < len(script_roster) else "MISSING"

            if verified_player != script_player:
                mismatches.append(f"    {role.upper():>7}: script has '{script_player}' but verified roster has '{verified_player}'")

        if mismatches:
            raise RosterMismatchError(
                f"\n{'═'*72}\n"
                f"  ❌ SIMULATION BLOCKED — ROSTER MISMATCH DETECTED\n"
                f"{'═'*72}\n"
                f"  Team: {team_code} ({entry['full_name']})\n"
                f"  Verified source: {entry.get('source', 'unknown')}\n"
                f"  Verified at: {entry.get('verified_at', 'unknown')}\n\n"
                f"  MISMATCHES:\n" +
                "\n".join(mismatches) +
                f"\n\n  Fix your prediction script to use the verified roster,\n"
                f"  or re-verify the roster if it has changed.\n"
                f"{'═'*72}\n"
            )

        return True  # All clear

    def get_roster(self, team_code):
        """Get a roster without enforcing the gate (for inspection only)."""
        return self._rosters.get(team_code)

    def get_status(self):
        """Return the status of all verified rosters."""
        status = {}
        for code, entry in self._rosters.items():
            stale = self._is_stale(entry.get("verified_at", ""))
            status[code] = {
                "full_name": entry.get("full_name", "Unknown"),
                "league": entry.get("league", "Unknown"),
                "players": list(entry.get("players", {}).values()),
                "verified_at": entry.get("verified_at", "Never"),
                "source": entry.get("source", "Unknown"),
                "status": "🔴 STALE" if stale else "✅ VERIFIED"
            }
        return status

    def get_verified_roster_list(self, team_code):
        """
        Convenience: returns the verified roster as an ordered list [Top, Jgl, Mid, ADC, Sup].
        This is what prediction scripts should use to populate their match dicts.
        """
        entry = self.require_verified_roster(team_code)
        return [entry["players"][role] for role in ROLES]


# ═══════════════════════════════════════════════════════════════
# CLI INTERFACE
# ═══════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(
        description="Roster Verification Gate — Quant-Elite 3.2",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ── verify ──
    verify_parser = subparsers.add_parser("verify", help="Verify/update a team's roster")
    verify_parser.add_argument("team_code", help="Team code (e.g., KT, BFX)")
    verify_parser.add_argument("--name", required=True, help="Full team name")
    verify_parser.add_argument("--league", required=True, help="League (LCK, LPL, LEC)")
    verify_parser.add_argument("--players", nargs=5, required=True,
                               metavar=("TOP", "JGL", "MID", "ADC", "SUP"),
                               help="5 player names in order: Top Jungle Mid ADC Support")
    verify_parser.add_argument("--subs", nargs="*", default=[],
                               help="Substitute players as role:name pairs (e.g., mid:Daystar)")
    verify_parser.add_argument("--source", default="manual", help="Data source (e.g., liquipedia)")

    # ── check ──
    check_parser = subparsers.add_parser("check", help="Check if a team's roster is verified")
    check_parser.add_argument("team_code", help="Team code to check")

    # ── cross-check ──
    xcheck_parser = subparsers.add_parser("cross-check", help="Cross-check a script roster against verified data")
    xcheck_parser.add_argument("team_code", help="Team code")
    xcheck_parser.add_argument("players", nargs=5, metavar=("TOP", "JGL", "MID", "ADC", "SUP"),
                               help="5 player names to cross-check")

    # ── status ──
    subparsers.add_parser("status", help="Show all verified rosters and their status")

    args = parser.parse_args()
    gate = RosterGate()

    if args.command == "verify":
        players = dict(zip(ROLES, args.players))
        subs = {}
        for s in args.subs:
            if ":" in s:
                role, name = s.split(":", 1)
                subs[role] = name

        entry = gate.verify_roster(
            team_code=args.team_code,
            full_name=args.name,
            league=args.league,
            players=players,
            subs=subs,
            source=args.source,
            verified_by="cli"
        )
        print(f"\n{'═'*72}")
        print(f"  ✅ ROSTER VERIFIED: {args.team_code} ({args.name})")
        print(f"{'═'*72}")
        print(f"  League:     {args.league}")
        print(f"  Players:    {list(players.values())}")
        if subs:
            print(f"  Subs:       {subs}")
        print(f"  Source:     {args.source}")
        print(f"  Verified:   {entry['verified_at']}")
        print(f"{'═'*72}\n")

    elif args.command == "check":
        try:
            entry = gate.require_verified_roster(args.team_code)
            print(f"\n  ✅ {args.team_code} ({entry['full_name']}): VERIFIED")
            print(f"     Players:  {list(entry['players'].values())}")
            print(f"     Source:   {entry.get('source', 'unknown')}")
            print(f"     Verified: {entry.get('verified_at', 'unknown')}\n")
        except (RosterNotVerifiedError, RosterStaleError) as e:
            print(str(e))
            sys.exit(1)

    elif args.command == "cross-check":
        try:
            gate.cross_check_roster(args.team_code, args.players)
            print(f"\n  ✅ {args.team_code}: Cross-check PASSED — script roster matches verified data.\n")
        except (RosterNotVerifiedError, RosterStaleError, RosterMismatchError) as e:
            print(str(e))
            sys.exit(1)

    elif args.command == "status":
        status = gate.get_status()
        if not status:
            print("\n  ⚠️  No rosters verified yet. Run 'verify' for each team before simulating.\n")
            return

        print(f"\n{'═'*72}")
        print(f"  📋 ROSTER VERIFICATION STATUS")
        print(f"{'═'*72}")
        for code, info in sorted(status.items()):
            print(f"\n  {info['status']} {code} ({info['full_name']}) — {info['league']}")
            print(f"     Players:  {info['players']}")
            print(f"     Source:   {info['source']}")
            print(f"     Verified: {info['verified_at']}")
        print(f"\n{'═'*72}\n")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
