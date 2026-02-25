import pytest
from sqlalchemy import text

from courseflow.allocator import attempt_registration
from courseflow.database import Course, SessionLocal, Student


COURSE_ID = 1


@pytest.fixture(autouse=True)
def setup_students():
    db = SessionLocal()

    for i in range(1000):
        student = db.query(Student).filter(Student.id == i).first()
        if not student:
            student = Student(id=i, name=f"Student {i}")
            db.add(student)

    course = db.query(Course).filter(Course.id == COURSE_ID).first()
    if not course:
        course = Course(id=COURSE_ID, name="Test Course", capacity=5, seats_taken=0)
        db.add(course)

    db.commit()
    db.close()

    yield

    db = SessionLocal()
    db.execute(text("DELETE FROM enrollments"))
    db.execute(text("DELETE FROM waitlist"))
    course = db.query(Course).filter(Course.id == COURSE_ID).first()
    if course:
        course.seats_taken = 0
        course.capacity = 5
    db.commit()
    db.close()


def test_waitlist_when_full():
    db = SessionLocal()
    course = db.query(Course).filter(Course.id == COURSE_ID).first()

    course.capacity = 0
    course.seats_taken = 0
    db.commit()
    db.close()

    result = attempt_registration(
        student_id=999, course_id=COURSE_ID, idempotency_key="unit_test_key"
    )

    assert result["status"] == "waitlisted"
