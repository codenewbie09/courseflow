import asyncio
import uuid

import httpx
import pytest

from courseflow.database import Enrollment, SessionLocal

COURSE_ID = 1


@pytest.mark.asyncio
async def test_priority_boost():
    async with httpx.AsyncClient() as client:
        # Low priority
        for i in range(3):
            await client.post(
                "http://127.0.0.1:8000/enroll",
                json={
                    "student_id": i,
                    "course_id": COURSE_ID,
                    "idempotency_key": str(uuid.uuid4()),
                    "priority": 0,
                },
            )

        # High priority
        await client.post(
            "http://127.0.0.1:8000/enroll",
            json={
                "student_id": 999,
                "course_id": COURSE_ID,
                "idempotency_key": str(uuid.uuid4()),
                "priority": 10,
            },
        )

    await asyncio.sleep(3)

    db = SessionLocal()
    enrolled_ids = [e.student_id for e in db.query(Enrollment).all()]

    assert 999 in enrolled_ids

    db.close()
