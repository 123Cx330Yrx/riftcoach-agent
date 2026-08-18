import os
from urllib.parse import quote

import requests
from dotenv import load_dotenv


class RiotClient:
    """Thin one-request Riot API client.

    Retry, circuit breaking, caching, and redacted error reporting belong to
    the Tool Runtime adapter rather than this HTTP transport.
    """

    def __init__(self, api_key: str | None = None, region: str | None = None):
        # Legacy scripts may still rely on local .env discovery. Deployment
        # composition passes both values explicitly and must not perform an
        # implicit dotenv read after its configuration has been validated.
        if api_key is None or region is None:
            load_dotenv()

        self.api_key = api_key if api_key is not None else os.getenv("RIOT_API_KEY")
        self.region = (
            region if region is not None else os.getenv("RIOT_REGION", "asia")
        )

        if not self.api_key:
            raise RuntimeError("RIOT_API_KEY is missing. Please set it in .env.")

        self.session = requests.Session()
        self.session.headers.update({"X-Riot-Token": self.api_key})

    def _get(self, url: str, timeout_s: float = 15):
        response = self.session.get(url, timeout=timeout_s)
        response.raise_for_status()
        return response.json()

    def get_account_by_riot_id(
        self,
        game_name: str,
        tag_line: str,
        *,
        timeout_s: float = 15,
    ):
        encoded_game_name = quote(game_name, safe="")
        encoded_tag_line = quote(tag_line, safe="")

        url = (
            f"https://{self.region}.api.riotgames.com"
            f"/riot/account/v1/accounts/by-riot-id/"
            f"{encoded_game_name}/{encoded_tag_line}"
        )
        return self._get(url, timeout_s)

    def get_recent_match_ids(
        self,
        puuid: str,
        count: int = 20,
        queue: int | None = 420,
        *,
        timeout_s: float = 15,
    ):
        query = f"start=0&count={count}"
        if queue is not None:
            query += f"&queue={queue}"

        url = (
            f"https://{self.region}.api.riotgames.com"
            f"/lol/match/v5/matches/by-puuid/{puuid}/ids?"
            f"{query}"
        )
        return self._get(url, timeout_s)

    def get_match_detail(
        self,
        match_id: str,
        *,
        timeout_s: float = 15,
    ):
        url = (
            f"https://{self.region}.api.riotgames.com"
            f"/lol/match/v5/matches/{match_id}"
        )
        return self._get(url, timeout_s)

    def get_match_timeline(
        self,
        match_id: str,
        *,
        timeout_s: float = 15,
    ):
        url = (
            f"https://{self.region}.api.riotgames.com"
            f"/lol/match/v5/matches/{match_id}/timeline"
        )
        return self._get(url, timeout_s)
