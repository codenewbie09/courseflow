import asyncio
import json
import logging
import time

import redis
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from courseflow.database import Course, SessionLocal
from courseflow.worker import process_queue

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import os

r = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    db=0,
    decode_responses=True
)

app = FastAPI(title="CourseFlow v2.1")


class EnrollRequest(BaseModel):
    student_id: int
    course_id: int
    idempotency_key: str
    priority: int = 0


@app.post("/enroll")
async def enroll(req: EnrollRequest):
    queue_key = f"queue:course:{req.course_id}"

    try:
        payload = json.dumps(
            {
                "student_id": req.student_id,
                "course_id": req.course_id,
                "idempotency_key": req.idempotency_key,
            }
        )

        # Priority logic
        score = (time.time() * 1_000_000) - (req.priority * 10_000)

        r.zadd(queue_key, {payload: score})

        rank = r.zrank(queue_key, payload)

        return {
            "status": "queued",
            "queue_position": rank + 1 if rank is not None else None,
        }

    except redis.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Redis unavailable")


@app.get("/metrics")
def metrics():
    db = SessionLocal()
    try:
        queue_depth = r.zcard("queue:course:1")

        course = db.query(Course).filter(Course.id == 1).first()

        return {
            "queue_depth": queue_depth,
            "seats_taken": course.seats_taken if course else None,
            "capacity": course.capacity if course else None,
            "status": "operational",
        }
    finally:
        db.close()


@app.on_event("startup")
async def startup():
    asyncio.create_task(process_queue(course_id=1))


def calculate_score(priority: int, base_time: float):
    return (base_time * 1_000_000) - (priority * 10_000)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
