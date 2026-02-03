import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, BackgroundTasks, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app import models, schemas, database, services

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn")

# --- LIFESPAN MANAGER ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize DB tables
    async with database.engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    yield
    # Shutdown logic (if any) would go here

app = FastAPI(title="Articence PBX Intern Task", lifespan=lifespan)

# --- ENDPOINTS ---

@app.post("/v1/call/init", status_code=201)
async def init_call(packet: schemas.CallCreate, db: AsyncSession = Depends(database.get_db)):
    """Initialize a call session."""
    new_call = models.Call(call_id=packet.call_id)
    db.add(new_call)
    await db.commit()
    return {"status": "Call initialized"}

@app.post("/v1/call/stream/{call_id}", status_code=202)
async def ingest_audio(
    call_id: str, 
    packet: schemas.AudioPacket, 
    db: AsyncSession = Depends(database.get_db)
):
    """
    Ingests audio packets. 
    Handles RACE CONDITIONS using 'with_for_update' (Row Locking).
    """
    async with db.begin(): # Transaction block
        # LOCK the row to prevent race conditions
        query = select(models.Call).filter(models.Call.call_id == call_id).with_for_update()
        result = await db.execute(query)
        call = result.scalars().first()

        if not call:
            # Non-blocking error for ingestion (just log it)
            logger.warning(f"Call {call_id} not found.")
            return {"status": "Ignored"}

        # Validate Order
        if packet.sequence != call.last_sequence + 1:
            logger.warning(f"Packet OOO: Expected {call.last_sequence + 1}, got {packet.sequence}")
            # We accept it anyway as per requirement "Do not block"
        
        # Update State
        call.last_sequence = packet.sequence
        # In a real app, we would append 'packet.data' to a buffer/storage here.
        
        await db.commit()
    
    return {"status": "Accepted"}

@app.post("/v1/call/complete/{call_id}")
async def end_call(
    call_id: str, 
    background_tasks: BackgroundTasks, 
    db: AsyncSession = Depends(database.get_db)
):
    """Triggers the AI processing state."""
    query = select(models.Call).filter(models.Call.call_id == call_id)
    result = await db.execute(query)
    call = result.scalars().first()

    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    call.state = models.CallState.COMPLETED
    await db.commit()

    # Trigger Background Processing (Non-Blocking)
    background_tasks.add_task(services.process_call_ai, call_id, database.AsyncSessionLocal)
    
    return {"status": "Processing started"}