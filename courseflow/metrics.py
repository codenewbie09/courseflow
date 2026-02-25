from prometheus_client import Counter, Histogram, Gauge, generate_latest

enrollment_requests_total = Counter(
    'enrollment_requests_total',
    'Total enrollment requests',
    ['status']
)

enrollment_latency_seconds = Histogram(
    'enrollment_latency_seconds',
    'Enrollment processing latency'
)

queue_depth = Gauge(
    'courseflow_queue_depth',
    'Current queue depth',
    ['course_id']
)

seats_taken = Gauge(
    'courseflow_seats_taken',
    'Seats taken in course',
    ['course_id']
)

capacity = Gauge(
    'courseflow_capacity',
    'Course capacity',
    ['course_id']
)
