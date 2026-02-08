from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime

class IngestEvent(BaseModel):
    content: str
    timestamp: datetime
    metadata: Dict[str, str] = {}