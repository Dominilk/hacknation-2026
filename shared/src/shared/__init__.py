from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer

class IngestEvent(BaseModel):
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)
    model_config = ConfigDict(extra="forbid")

    @field_serializer("timestamp")
    def _serialize_timestamp(self, value: datetime) -> str:
        return value.isoformat()

    def to_json(self) -> str:
        """Return a JSON string payload."""
        return self.model_dump_json()

    def to_dict(self) -> dict:
        """Return a JSON-safe dict payload."""
        return self.model_dump(mode="json")
