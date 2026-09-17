"""
Get Match IDs from Riot API using Riot ID.

Usage:
    python scripts/get_match_ids.py --riot-id "Doublelift#NA1" --count 10
    python scripts/get_match_ids.py --riot-ids "Doublelift#NA1" "Faker#KR1" --count 5
"""

import sys
from pathlib import Path
import argparse
import requests
import urllib.parse

sys.path.insert(0, str(Path(__file__).parent / "src"))

from config import RIOT_API_KEY


def get_puuid_by_riot_id(riot_id: str) -> str:
    """Get PUUID using Riot ID (GameName#Tagline)."""
    if "#" not in riot_id:
        print(f"Invalid format: {riot_id} (use GameName#Tagline)")
        return None

    game_name, tag_line = riot_id.split("#", 1)
    game_name_encoded = urllib.parse.quote(game_name)
    tag_line_encoded = urllib.parse.quote(tag_line)

    url = f"https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name_encoded}/{tag_line_encoded}"
    headers = {"X-Riot-Token": RIOT_API_KEY}

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 404:
            print(f"  Not found: {riot_id}")
            return None

        response.raise_for_status()
        data = response.json()
        print(f"  Found: {data.get('gameName')}#{data.get('tagLine')}")
        return data.get("puuid")

    except Exception as e:
        print(f"  Error: {e}")
        return None


def get_match_ids_by_puuid(puuid: str, count: int = 20) -> list:
    """Get recent match IDs for a PUUID."""
    url = f"https://americas.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
    headers = {"X-Riot-Token": RIOT_API_KEY}
    params = {"start": 0, "count": min(count, 100), "type": "ranked"}

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        match_ids = response.json()
        print(f"  {len(match_ids)} ranked matches")
        return match_ids

    except Exception as e:
        print(f"  Error: {e}")
        return []


def main():
    parser = argparse.ArgumentParser(
        description="Fetch match IDs from Riot API using Riot ID",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/get_match_ids.py --riot-id "Doublelift#NA1" --count 10
  python scripts/get_match_ids.py --riot-ids "Doublelift#NA1" "Faker#KR1" --count 5
  python scripts/get_match_ids.py --riot-id "Doublelift#NA1" --output match_ids.txt

Note: Use Riot ID format "GameName#Tagline" (e.g., #NA1, #EUW, #KR1)
        """,
    )

    parser.add_argument("--riot-id", help='Single Riot ID (e.g., "Doublelift#NA1")')
    parser.add_argument("--riot-ids", nargs="+", help="Multiple Riot IDs")
    parser.add_argument("--count", type=int, default=10, help="Matches per player (default: 10)")
    parser.add_argument("--output", help="Output file (optional)")

    args = parser.parse_args()

    if args.riot_id:
        riot_ids = [args.riot_id]
    elif args.riot_ids:
        riot_ids = args.riot_ids
    else:
        print("No Riot ID specified. Use --riot-id or --riot-ids")
        return

    print(f"Fetching matches for: {', '.join(riot_ids)}")

    all_match_ids = []
    for riot_id in riot_ids:
        puuid = get_puuid_by_riot_id(riot_id)
        if not puuid:
            continue
        match_ids = get_match_ids_by_puuid(puuid, args.count)
        all_match_ids.extend(match_ids)

    unique_match_ids = list(set(all_match_ids))
    print(f"\nFound {len(unique_match_ids)} unique matches:")

    for i, match_id in enumerate(unique_match_ids, 1):
        print(f"  {i:2d}. {match_id}")

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            for match_id in unique_match_ids:
                f.write(f"{match_id}\n")
        print(f"\nSaved to: {args.output}")

    if unique_match_ids:
        ids_to_show = " ".join(unique_match_ids[:5])
        print(f"\nUsage: python scripts/generate_tasks.py --match-ids {ids_to_show}")


if __name__ == "__main__":
    main()
