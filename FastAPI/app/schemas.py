from pydantic import BaseModel
from typing import Optional

class AudioPacket(BaseModel):
    sequence: int
    data: str
    timestamp: float

class CallCreate(BaseModel):
    call_id: str