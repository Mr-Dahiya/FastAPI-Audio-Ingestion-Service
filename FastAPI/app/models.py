import enum
from sqlalchemy import Column, Integer, String, Enum, DateTime, func
from app.database import Base

class CallState(str, enum.Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    PROCESSING_AI = "PROCESSING_AI"
    ARCHIVED = "ARCHIVED"
    FAILED = "FAILED"

class Call(Base):
    __tablename__ = "calls"

    id = Column(Integer, primary_key=True, index=True)
    call_id = Column(String, unique=True, index=True)
    state = Column(Enum(CallState), default=CallState.IN_PROGRESS)
    transcript = Column(String, nullable=True)
    last_sequence = Column(Integer, default=0) # Tracks packet order
    created_at = Column(DateTime, server_default=func.now())