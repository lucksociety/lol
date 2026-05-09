import os
import json
import time
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional

class RiotAPIClient:
    def __init__(self, region: str = "na1", routing_region: str = "americas"):
        self.region = region
        self.routing_region = routing_region
        # Attempt to get API key from environment
        self.api_key = os.getenv("RIOT_API_KEY")
        self.base_url = f"https://{region}.api.riotgames.com"
        self.routing_url = f"https://{routing_region}.api.riotgames.com"

    def _request(self, url: str) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("RIOT_API_KEY is not set.")
        
        req = urllib.request.Request(url, headers={"X-Riot-Token": self.api_key})
        
        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                retry_after = int(e.headers.get("Retry-After", 1))
                print(f"Rate limited. Retrying after {retry_after}s...")
                time.sleep(retry_after)
                return self._request(url)
            raise
        
    def get_summoner_by_name(self, summoner_name: str, tag_line: str) -> Dict[str, Any]:
        url = f"{self.routing_url}/riot/account/v1/accounts/by-riot-id/{summoner_name}/{tag_line}"
        return self._request(url)

    def get_match_ids_by_puuid(self, puuid: str, start: int = 0, count: int = 20, queue: int = 420) -> List[str]:
        url = f"{self.routing_url}/lol/match/v5/matches/by-puuid/{puuid}/ids?start={start}&count={count}&queue={queue}"
        return self._request(url)
        
    def get_match_by_id(self, match_id: str) -> Dict[str, Any]:
        url = f"{self.routing_url}/lol/match/v5/matches/{match_id}"
        return self._request(url)
        
    def get_match_timeline_by_id(self, match_id: str) -> Dict[str, Any]:
        url = f"{self.routing_url}/lol/match/v5/matches/{match_id}/timeline"
        return self._request(url)

    def get_live_game_by_summoner(self, puuid: str) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/lol/spectator/v5/active-games/by-summoner/{puuid}"
        try:
            return self._request(url)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            raise
