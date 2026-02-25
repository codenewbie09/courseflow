import logging
import time

from sqlalchemy.exc import IntegrityError

from courseflow.database import Course, Enrollment, SessionLocal, Waitlist

logger = logging.getLogger(__name__)


def attempt_registration(student_id: int, course_id: int, idempotency_key: str):
    db = SessionLocal()

    try:
        start = time.time()

        # Proper ORM transaction
        with db.begin():
            # Lock course row
            course = (
                db.query(Course)
                .filter(Course.id == course_id)
                .with_for_update()
                .first()
            )

            if not course:
                return {"status": "error", "message": "Course not found"}

            # Idempotency check
            existing = (
                db.query(Enrollment)
                .filter(Enrollment.idempotency_key == idempotency_key)
                .first()
            )

            if existing:
                return {"status": "success", "message": "Already processed"}

            # Capacity check
            if course.seats_taken >= course.capacity:
                # Add to waitlist safely
                waitlist_entry = Waitlist(student_id=student_id, course_id=course_id)

                db.add(waitlist_entry)

                return {"status": "waitlisted", "message": "Course full"}

            # Increment seat
            course.seats_taken += 1

            enrollment = Enrollment(
                student_id=student_id,
                course_id=course_id,
                idempotency_key=idempotency_key,
            )

            db.add(enrollment)

        duration = time.time() - start
        logger.info(f"Registered {student_id} in {duration:.4f}s")

        return {"status": "success", "message": "Enrolled"}

    except IntegrityError:
        # Likely idempotency or duplicate waitlist
        db.rollback()
        return {"status": "success", "message": "Already processed"}

    except Exception as e:
        db.rollback()
        logger.error(f"Allocation error: {e}")
        return {"status": "error", "message": "Internal error"}

    finally:
        db.close()
