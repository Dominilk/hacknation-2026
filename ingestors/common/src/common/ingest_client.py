import httpx
from .models import IngestEvent

class IngestAPIClient:
    def __init__(self, base_url: str, api_key: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.headers = {}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

    async def ingest(self, event: IngestEvent) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/ingest",
                json=event.model_dump(),
                headers=self.headers,
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()