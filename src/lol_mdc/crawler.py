import requests
import json
from typing import Dict, Any

class RiotAPIClient:
    def __init__(self, api_key: str, region: str = "na1"):
        self.api_key = api_key
        self.region = region
        self.base_url = f"https://{region}.api.riotgames.com"
        self.headers = {"X-Riot-Token": api_key}
    
    def get_match_timeline(self, match_id: str) -> Dict[str, Any]:
        """Fetch detailed timeline for a match"""
        url = f"{self.base_url}/lol/match/v5/matches/{match_id}/timeline"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_match_details(self, match_id: str) -> Dict[str, Any]:
        """Fetch match metadata and end-game stats"""
        url = f"{self.base_url}/lol/match/v5/matches/{match_id}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
