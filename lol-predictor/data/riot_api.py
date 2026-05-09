import os
import requests
import time
from ratelimit import limits, sleep_and_retry
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional

load_dotenv()

RIOT_API_KEY = os.getenv("RIOT_API_KEY")

class RiotAPIClient:
    def __init__(self, region: str = "na1", routing_region: str = "americas"):
        self.region = region
        self.routing_region = routing_region
        self.headers = {"X-Riot-Token": RIOT_API_KEY}
        self.base_url = f"https://{region}.api.riotgames.com"
        self.routing_url = f"https://{routing_region}.api.riotgames.com"

    @sleep_and_retry
    @limits(calls=20, period=1) # 20 requests every 1 second
    @limits(calls=100, period=120) # 100 requests every 2 minutes
    def _request(self, url: str) -> Dict[str, Any]:
        if not RIOT_API_KEY:
            raise ValueError("RIOT_API_KEY is not set. Check your .env file.")
        response = requests.get(url, headers=self.headers)
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 1))
            time.sleep(retry_after)
            return self._request(url)
        response.raise_for_status()
        return response.json()
        
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
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise
