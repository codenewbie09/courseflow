import uuid

from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/courseflow"
engine = create_engine(DATABASE_URL)

app = FastAPI()


class RegisterRequest(BaseModel):
    student_id: str
    course_id: int
    idempotency_key: str


@app.post("/register")
def register(req: RegisterRequest):
    try:
        with engine.begin() as conn:
            # Lock the course row
            course = conn.execute(
                text("""
                    SELECT seats_taken, capacity
                    FROM courses
                    WHERE id = :id
                    FOR UPDATE
                """),
                {"id": req.course_id},
            ).fetchone()

            if not course:
                return {"error": "Course not found"}

            seats_taken, capacity = course

            # Check idempotency inside transaction
            existing = conn.execute(
                text("""
                    SELECT id FROM registrations
                    WHERE idempotency_key = :key
                """),
                {"key": req.idempotency_key},
            ).fetchone()

            if existing:
                return {"status": "SUCCESS", "message": "Already processed"}

            if seats_taken >= capacity:
                return {"status": "FULL"}

            # Increment seats
            conn.execute(
                text("""
                    UPDATE courses
                    SET seats_taken = seats_taken + 1
                    WHERE id = :id
                """),
                {"id": req.course_id},
            )

            # Insert registration
            conn.execute(
                text("""
                    INSERT INTO registrations (id, student_id, course_id, idempotency_key)
                    VALUES (:id, :student_id, :course_id, :key)
                """),
                {
                    "id": str(uuid.uuid4()),
                    "student_id": req.student_id,
                    "course_id": req.course_id,
                    "key": req.idempotency_key,
                },
            )

            return {"status": "SUCCESS"}

    except IntegrityError:
        # Handles rare race where duplicate insert happens
        return {"status": "SUCCESS", "message": "Already processed"}
