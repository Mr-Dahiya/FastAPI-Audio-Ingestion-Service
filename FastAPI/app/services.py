import asyncio
import random
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import Call, CallState

logger = logging.getLogger("uvicorn")

class AIServiceUnavailable(Exception):
    pass

# --- THE FLAKY SERVICE ---
async def mock_external_ai_service(audio_data: str) -> str:
    """Simulates 25% failure rate and 1-3s latency."""
    await asyncio.sleep(random.uniform(1, 3))  # Variable Latency
    
    if random.random() < 0.25:  # 25% Failure Rate
        logger.warning("AI Service returned 503 Unavailable!")
        raise AIServiceUnavailable("Service Unavailable")
    
    return "This is a simulated transcription of the audio."

# --- RETRY STRATEGY (Exponential Backoff) ---
@retry(
    stop=stop_after_attempt(5), 
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(AIServiceUnavailable)
)
async def reliable_transcribe(audio_data: str) -> str:
    return await mock_external_ai_service(audio_data)

# --- BACKGROUND ORCHESTRATOR ---
async def process_call_ai(call_id: str, db_session_factory):
    """Background task that manages DB state and calls AI."""
    async with db_session_factory() as db:
        try:
            # 1. Fetch Call & Update State to PROCESSING_AI
            result = await db.execute(select(Call).filter(Call.call_id == call_id))
            call = result.scalars().first()
            if not call:
                return
            
            call.state = CallState.PROCESSING_AI
            await db.commit()

            # 2. Call AI with Retries
            transcript = await reliable_transcribe("dummy_merged_audio_data")

            # 3. Save Result & Finish
            call.transcript = transcript
            call.state = CallState.ARCHIVED  # Corrected from FINISHED
            await db.commit()
            logger.info(f"Call {call_id} processed successfully.")

        except Exception as e:
            logger.error(f"Failed to process call {call_id}: {e}")
            # If all retries fail, mark as FAILED
            call.state = CallState.FAILED
            await db.commit()