import asyncio
import uuid

import httpx
import pytest
from sqlalchemy import text

from courseflow.database import Course, SessionLocal

COURSE_ID = 1


@pytest.mark.asyncio
async def test_waitlist_behavior():
    db = SessionLocal()
    course = db.query(Course).filter(Course.id == COURSE_ID).first()
    course.capacity = 2
    db.commit()
    db.close()

    async with httpx.AsyncClient() as client:
        for i in range(5):
            await client.post(
                "http://127.0.0.1:8000/enroll",
                json={
                    "student_id": i,
                    "course_id": COURSE_ID,
                    "idempotency_key": str(uuid.uuid4()),
                    "priority": 0,
                },
            )

    await asyncio.sleep(4)

    db = SessionLocal()
    seats = db.query(Course).filter(Course.id == COURSE_ID).first().seats_taken
    waitlist_count = db.execute(text("SELECT COUNT(*) FROM waitlist")).scalar()

    assert seats == 2
    assert waitlist_count == 3

    db.close()
