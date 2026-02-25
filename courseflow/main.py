import os
import signal
import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager

import redis
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from courseflow.database import Course, SessionLocal
from courseflow.worker import process_queue

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

r = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    db=0,
    decode_responses=True
)

worker_task = None
shutdown_event = asyncio.Event()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global worker_task
    worker_task = asyncio.create_task(process_queue(course_id=1))
    logger.info("Worker started")
    yield
    logger.info("Shutting down worker...")
    shutdown_event.set()
    if worker_task:
        try:
            await asyncio.wait_for(worker_task, timeout=5.0)
        except asyncio.TimeoutError:
            worker_task.cancel()
    logger.info("Worker stopped")


app = FastAPI(title="CourseFlow v2.1", lifespan=lifespan)


class EnrollRequest(BaseModel):
    student_id: int
    course_id: int
    idempotency_key: str
    priority: int = 0


@app.get("/health")
def health():
    return {"status": "ok"}


from sqlalchemy import text

@app.get("/ready")
def ready():
    try:
        r.ping()
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return {"status": "ready", "redis": "ok", "database": "ok"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service not ready: {str(e)}")


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
def metrics(course_id: int = 1):
    db = SessionLocal()
    try:
        queue_depth = r.zcard(f"queue:course:{course_id}")
        course = db.query(Course).filter(Course.id == course_id).first()

        return {
            "course_id": course_id,
            "queue_depth": queue_depth,
            "seats_taken": course.seats_taken if course else None,
            "capacity": course.capacity if course else None,
            "status": "operational",
        }
    finally:
        db.close()


@app.get("/courses")
def list_courses():
    db = SessionLocal()
    try:
        courses = db.query(Course).all()
        return [
            {
                "id": c.id,
                "name": c.name,
                "capacity": c.capacity,
                "seats_taken": c.seats_taken,
            }
            for c in courses
        ]
    finally:
        db.close()


def calculate_score(priority: int, base_time: float):
    return (base_time * 1_000_000) - (priority * 10_000)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("SERVER_PORT", "8000")))
