import asyncio
import uuid

import httpx
import pytest

from courseflow.database import Enrollment, SessionLocal

COURSE_ID = 1


@pytest.mark.asyncio
async def test_idempotency_protection():
    key = str(uuid.uuid4())

    async with httpx.AsyncClient() as client:
        await asyncio.gather(
            client.post(
                "http://127.0.0.1:8000/enroll",
                json={
                    "student_id": 1,
                    "course_id": COURSE_ID,
                    "idempotency_key": key,
                    "priority": 0,
                },
            ),
            client.post(
                "http://127.0.0.1:8000/enroll",
                json={
                    "student_id": 1,
                    "course_id": COURSE_ID,
                    "idempotency_key": key,
                    "priority": 0,
                },
            ),
        )

    await asyncio.sleep(2)

    db = SessionLocal()
    count = db.query(Enrollment).filter(Enrollment.idempotency_key == key).count()

    assert count == 1

    db.close()
