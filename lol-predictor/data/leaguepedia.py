import mwclient
from ratelimit import limits, sleep_and_retry
from datetime import datetime

class LeaguepediaClient:
    def __init__(self):
        self.site = mwclient.Site('lol.fandom.com', path='/')

    @sleep_and_retry
    @limits(calls=1, period=2)  # Conservative rate limit for Leaguepedia
    def query_cargo(self, table: str, fields: str, where: str = None, order_by: str = None, limit: int = 500, offset: int = 0):
        params = {
            'action': 'cargoquery',
            'tables': table,
            'fields': fields,
            'where': where,
            'order_by': order_by,
            'limit': limit,
            'offset': offset,
            'format': 'json'
        }
        response = self.site.api(**params)
        return [item['title'] for item in response.get('cargoquery', [])]

    def fetch_recent_games(self, tournament: str = "LCK 2024 Spring", limit: int = 100):
        where = f"Tournament LIKE '%{tournament}%'"
        fields = "GameId, MatchId, Tournament, DateTime_UTC, Team1, Team2, WinTeam, Duration, Team1Bans, Team2Bans, Team1Picks, Team2Picks, Team1Side, Team2Side, Patch"
        
        games = []
        offset = 0
        while len(games) < limit:
            batch = self.query_cargo("ScoreboardGames", fields, where=where, offset=offset, order_by="DateTime_UTC DESC", limit=min(limit - len(games), 500))
            if not batch:
                break
            games.extend(batch)
            offset += len(batch)
            if len(batch) < 500:
                break
        return games
