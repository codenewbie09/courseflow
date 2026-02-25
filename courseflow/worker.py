import asyncio
import json
import logging

import redis

from courseflow.allocator import attempt_registration

logger = logging.getLogger(__name__)

import os

r = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    db=0,
    decode_responses=True
)


async def process_queue(course_id: int):
    queue_key = f"queue:course:{course_id}"

    logger.info(f"Worker started for Course {course_id}")

    while True:
        try:
            data = r.zpopmin(queue_key)

            if not data:
                await asyncio.sleep(0.5)
                continue

            payload_str, _ = data[0]
            payload = json.loads(payload_str)

            result = attempt_registration(
                student_id=payload["student_id"],
                course_id=payload["course_id"],
                idempotency_key=payload["idempotency_key"],
            )

            logger.info(f"Processed: {result['status']}")

        except Exception as e:
            logger.error(f"Worker error: {e}")
            await asyncio.sleep(1)
