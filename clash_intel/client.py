import aiohttp
import urllib.parse
from typing import Optional, Dict, Any, Tuple

class ClashAPIClient:
    """Encapsulated HTTP client for the Clash of Clans API proxy layer."""

    BASE_URL = "https://cocproxy.royaleapi.dev/v1"

    def __init__(self, token: str):
        if not token:
            raise ValueError("API token authentication is required.")
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }

    @staticmethod
    def format_tag(tag: str) -> str:
        clean_tag = tag.strip().upper()
        if not clean_tag.startswith("#"):
            clean_tag = f"#{clean_tag}"
        return urllib.parse.quote(clean_tag)

    async def _fetch(self, session: aiohttp.ClientSession, endpoint: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        url = f"{self.BASE_URL}/{endpoint}"
        try:
            async with session.get(url, headers=self.headers) as response:
                if response.status == 200:
                    return await response.json(), None
                if response.status == 403:
                    return None, "Invalid API Token. Verify your key configuration."
                if response.status == 404:
                    return None, "Target resource tag not found."
                return None, f"API Error: HTTP {response.status}"
        except Exception as e:
            return None, f"Connection failed: {str(e)}"

    async def get_player_profile(self, tag: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        async with aiohttp.ClientSession() as session:
            return await self._fetch(session, f"players/{self.format_tag(tag)}")

    async def get_player_battlelog(self, tag: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        async with aiohttp.ClientSession() as session:
            return await self._fetch(session, f"players/{self.format_tag(tag)}/battlelog")

    async def get_clan_data(self, tag: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        async with aiohttp.ClientSession() as session:
            return await self._fetch(session, f"clans/{self.format_tag(tag)}")

    async def get_war_log(self, tag: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        async with aiohttp.ClientSession() as session:
            return await self._fetch(session, f"clans/{self.format_tag(tag)}/warlog")

    async def get_raid_seasons(self, tag: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        async with aiohttp.ClientSession() as session:
            return await self._fetch(session, f"clans/{self.format_tag(tag)}/capitalraidseasons")

    async def fetch_bulk_profiles(self, tags: list) -> list:
        async with aiohttp.ClientSession() as session:
            tasks = [self._fetch(session, f"players/{self.format_tag(t)}") for t in tags]
            results = await asyncio.gather(*tasks)
            return [r[0] for r in results if r[0] is not None]
