import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app

BASE_URL = "http://localhost:8000"

@pytest.mark.asyncio
async def test_race_condition():
    """
    Simulates two concurrent requests trying to update the sequence.
    Without DB Locking, the sequence might not increment correctly.
    """
    call_id = "race_test_final"
    
    # Use ASGITransport to fix deprecation warning
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as ac:
        # 1. Init Call
        await ac.post("/v1/call/init", json={"call_id": call_id})

        # 2. Fire two packets simultaneously
        payload1 = {"sequence": 1, "data": "audio1", "timestamp": 100.1}
        payload2 = {"sequence": 2, "data": "audio2", "timestamp": 100.2}

        # We use asyncio.gather to hit the API at the exact same time
        task1 = ac.post(f"/v1/call/stream/{call_id}", json=payload1)
        task2 = ac.post(f"/v1/call/stream/{call_id}", json=payload2)

        responses = await asyncio.gather(task1, task2)

        # 3. Assertions
        assert responses[0].status_code == 202
        assert responses[1].status_code == 202

        print("\nRace condition test passed: Both packets accepted.")