import os
import time
from urllib.parse import quote

import requests
from dotenv import load_dotenv


class RiotClient:
    def __init__(self, api_key: str | None = None, region: str | None = None):
        load_dotenv()

        self.api_key = api_key or os.getenv("RIOT_API_KEY")
        self.region = region or os.getenv("RIOT_REGION", "asia")

        if not self.api_key:
            raise RuntimeError("RIOT_API_KEY is missing. Please set it in .env.")

        self.session = requests.Session()
        self.session.headers.update({"X-Riot-Token": self.api_key})

    def _get(self, url: str, timeout: int = 15):
        response = self.session.get(url, timeout=timeout)

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", "3"))
            print(f"[WARN] Rate limited. Sleeping {retry_after} seconds...")
            time.sleep(retry_after)
            response = self.session.get(url, timeout=timeout)

        if response.status_code >= 400:
            print("\n[ERROR] Riot API request failed.")
            print("URL:", url)
            print("Status:", response.status_code)
            print("Response:", response.text[:500])
            response.raise_for_status()

        return response.json()

    def get_account_by_riot_id(self, game_name: str, tag_line: str):
        encoded_game_name = quote(game_name, safe="")
        encoded_tag_line = quote(tag_line, safe="")

        url = (
            f"https://{self.region}.api.riotgames.com"
            f"/riot/account/v1/accounts/by-riot-id/"
            f"{encoded_game_name}/{encoded_tag_line}"
        )

        return self._get(url)

    def get_recent_match_ids(
        self,
        puuid: str,
        count: int = 20,
        queue: int | None = 420,
    ):
        query = f"start=0&count={count}"

        if queue is not None:
            query += f"&queue={queue}"

        url = (
            f"https://{self.region}.api.riotgames.com"
            f"/lol/match/v5/matches/by-puuid/{puuid}/ids?"
            f"{query}"
        )

        return self._get(url)

    def get_match_detail(self, match_id: str):
        url = (
            f"https://{self.region}.api.riotgames.com"
            f"/lol/match/v5/matches/{match_id}"
        )
        return self._get(url)

    def get_match_timeline(self, match_id: str):
        url = (
            f"https://{self.region}.api.riotgames.com"
            f"/lol/match/v5/matches/{match_id}/timeline"
        )
        return self._get(url)