import asyncio

import httpx


async def send_request(i):
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "http://127.0.0.1:8000/register",
            json={"student_id": str(i), "course_id": 1, "idempotency_key": str(i)},
        )
        return r.json()


async def main():
    tasks = [send_request(1) for _ in range(50)]
    results = await asyncio.gather(*tasks)
    print(results.count({"status": "SUCCESS"}), "success")


asyncio.run(main())
