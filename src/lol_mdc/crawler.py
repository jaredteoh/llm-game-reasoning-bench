import requests
import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class RiotAPIClient:
    def __init__(self, api_key: str, region: str = "na1"):
        self.api_key = api_key
        self.region = region
        self.base_url = f"https://{region}.api.riotgames.com"
        self.headers = {"X-Riot-Token": api_key}
    
    def get_match_timeline(self, match_id: str) -> Dict[str, Any]:
        """Fetch detailed timeline for a match"""
        url = f"{self.base_url}/lol/match/v5/matches/{match_id}/timeline"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching match timeline for {match_id}: {e}")
            return None
    
    def get_match_details(self, match_id: str) -> Dict[str, Any]:
        """Fetch match metadata and end-game stats"""
        url = f"{self.base_url}/lol/match/v5/matches/{match_id}"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching match details for {match_id}: {e}")
            return None
