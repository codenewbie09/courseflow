import pytest
from sqlalchemy import text

from courseflow.database import Course, SessionLocal, Student


COURSE_ID = 1
DEFAULT_CAPACITY = 5


@pytest.fixture(autouse=True)
def reset_database():
    db = SessionLocal()

    course = db.query(Course).filter(Course.id == COURSE_ID).first()
    if course:
        course.seats_taken = 0
        course.capacity = DEFAULT_CAPACITY

    db.execute(text("DELETE FROM enrollments"))
    db.execute(text("DELETE FROM waitlist"))

    for i in range(10):
        student = db.query(Student).filter(Student.id == i).first()
        if not student:
            student = Student(id=i, name=f"Student {i}")
            db.add(student)

    db.commit()
    db.close()

    yield
