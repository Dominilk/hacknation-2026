from pydantic import BaseModel, Field, ConfigDict
import yaml
import os
import httpx
import datetime

from shared import IngestEvent

class Config(BaseModel):
    ingestion_endpoint: str = Field()
    ingestion_api_key: str | None = Field(default=None)
    model_config = ConfigDict(extra='allow')

def load_config(config_path: str = "config.yaml") -> Config:
    with open(config_path, 'r') as f:
        config_data = yaml.safe_load(f)
    return Config(**config_data)

class IngestAPIClient:
    def __init__(self, url: str, api_key: str | None = None):
        self.url = url
        self.headers = {}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

    async def ingest(self, data: str) -> dict:
        async with httpx.AsyncClient() as client:
            event = IngestEvent(content=data)
            resp = await client.post(
                f"{self.url}",
                json=event.to_dict(),
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()
