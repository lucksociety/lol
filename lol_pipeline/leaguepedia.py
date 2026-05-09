import json
import urllib.request
import urllib.parse
from typing import List, Dict, Any, Optional

class LeaguepediaClient:
    def __init__(self):
        self.base_url = "https://lol.fandom.com/api.php"

    def _query(self, params: Dict[str, str]) -> Dict[str, Any]:
        params.update({
            "action": "cargoquery",
            "format": "json"
        })
        url = f"{self.base_url}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": "AntigravityBot/1.0"})
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))

    def fetch_games_for_league(self, league: str, start_date: Optional[str] = None) -> List[Dict[str, Any]]:
        where = f"L.League = '{league}'"
        if start_date:
            where += f" AND L.DateTime_UTC > '{start_date}'"

        params = {
            "tables": "ScoreboardGames=G, ScoreboardLeagueRuns=L",
            "join_on": "G.MatchId=L.MatchId",
            "fields": "G.GameId, G.MatchId, G.Tournament, G.DateTime_UTC, G.Team1, G.Team2, G.WinTeam, G.Duration, G.Patch, G.Team1Bans, G.Team2Bans, G.Team1Picks, G.Team2Picks, G.Team1Side, G.Team2Side",
            "where": where,
            "order_by": "G.DateTime_UTC ASC",
            "limit": "50"
        }
        
        result = self._query(params)
        return [row['title'] for row in result.get('cargoquery', [])]

    def fetch_player_stats(self, game_ids: List[str]) -> List[Dict[str, Any]]:
        if not game_ids:
            return []
        
        # Cargo has limits on IN clauses, we'll process in chunks if needed, 
        # but for this refactor we'll do a simple limited query
        where = "GameId IN ('" + "','".join(game_ids[:20]) + "')"
        
        params = {
            "tables": "ScoreboardPlayers=P",
            "fields": "P.GameId, P.Name, P.Team, P.Champion, P.Role, P.Kills, P.Deaths, P.Assists, P.Gold, P.CS, P.DamageToChampions, P.VisionScore",
            "where": where,
            "limit": "500"
        }
        
        result = self._query(params)
        return [row['title'] for row in result.get('cargoquery', [])]

    def fetch_recent_games(self, tournament: str, limit: int = 10) -> List[Dict[str, Any]]:
        params = {
            "tables": "ScoreboardGames=G",
            "fields": "G.GameId, G.MatchId, G.Tournament, G.DateTime_UTC, G.Team1, G.Team2, G.WinTeam, G.Duration, G.Patch, G.Team1Picks, G.Team2Picks",
            "where": f"G.Tournament = '{tournament}'",
            "order_by": "G.DateTime_UTC DESC",
            "limit": str(limit)
        }
        result = self._query(params)
        return [row['title'] for row in result.get('cargoquery', [])]
