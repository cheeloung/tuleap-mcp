import httpx
from typing import Any, Dict, List, Optional


class TuleapAPIError(Exception):
    pass


class TuleapClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_url = f"{self.base_url}/api/v1"
        self.headers = {
            "X-Auth-AccessKey": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        url = f"{self.api_url}/{endpoint}"
        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, headers=self.headers, **kwargs)
            try:
                response.raise_for_status()
                if response.status_code == 204 or not response.content:
                    return None
                return response.json()
            except httpx.HTTPStatusError as e:
                error_detail = e.response.text
                try:
                    error_detail = e.response.json()
                except ValueError:
                    pass
                raise TuleapAPIError(
                    f"Tuleap API Error {e.response.status_code}: {error_detail}"
                )

    async def get(self, endpoint: str, params: Optional[Dict] = None) -> Any:
        return await self._request("GET", endpoint, params=params)

    async def get_paginated(self, endpoint: str, params: Optional[Dict] = None) -> List[Any]:
        params = dict(params or {})
        params.setdefault("limit", 50)
        params["offset"] = 0
        results = []
        async with httpx.AsyncClient() as client:
            while True:
                response = await client.request(
                    "GET", f"{self.api_url}/{endpoint}", headers=self.headers, params=params
                )
                response.raise_for_status()
                data = response.json()
                results.extend(data if isinstance(data, list) else [data])
                total = int(response.headers.get("X-Pagination-Size", len(results)))
                params["offset"] += params["limit"]
                if params["offset"] >= total:
                    break
        return results

    async def download(self, endpoint: str) -> httpx.Response:
        url = f"{self.api_url}/{endpoint}"
        async with httpx.AsyncClient() as client:
            response = await client.request("GET", url, headers=self.headers)
            response.raise_for_status()
            return response

    async def post(self, endpoint: str, json: Optional[Dict] = None) -> Any:
        return await self._request("POST", endpoint, json=json)

    async def put(self, endpoint: str, json: Optional[Dict] = None) -> Any:
        return await self._request("PUT", endpoint, json=json)
