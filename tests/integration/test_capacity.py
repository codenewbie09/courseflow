import asyncio
import uuid

import httpx
import pytest

from courseflow.database import Course, SessionLocal

TOTAL_REQUESTS = 20
COURSE_ID = 1


async def send_request(i):
    async with httpx.AsyncClient() as client:
        await client.post(
            "http://127.0.0.1:8000/enroll",
            json={
                "student_id": i,
                "course_id": COURSE_ID,
                "idempotency_key": str(uuid.uuid4()),
                "priority": 0,
            },
        )


@pytest.mark.asyncio
async def test_capacity_not_exceeded():
    tasks = [send_request(i) for i in range(TOTAL_REQUESTS)]
    await asyncio.gather(*tasks)

    await asyncio.sleep(3)

    db = SessionLocal()
    course = db.query(Course).filter(Course.id == COURSE_ID).first()

    assert course.seats_taken <= course.capacity

    db.close()
