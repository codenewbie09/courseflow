# CourseFlow v2.1 - Course Enrollment System

A distributed course enrollment system with Redis-based priority queue, PostgreSQL persistence, and async worker processing.

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│  FastAPI    │────▶│    Redis    │
│             │     │   Server    │     │   Queue     │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │   Worker    │
                                        │  (Async)    │
                                        └──────┬──────┘
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │ PostgreSQL  │
                                        │  Database   │
                                        └─────────────┘
```

## Features

- **Priority Queue**: Redis sorted sets with score-based prioritization
- **Idempotency**: Unique keys prevent duplicate enrollments
- **Concurrency**: Row-level locking (`SELECT FOR UPDATE`) prevents race conditions
- **Waitlist**: Automatic waitlist when course is full
- **Async Processing**: Background worker processes queue independently
- **Metrics**: Real-time queue depth and enrollment stats

## Quick Start

### Prerequisites
- PostgreSQL (port 5432)
- Redis (port 6379)
- Python 3.13+

### Docker Setup

```bash
# Run PostgreSQL
docker run -d --name postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=courseflow \
  -p 5432:5432 postgres

# Run Redis
docker run -d --name redis \
  -p 6380:6379 redis

# Set environment variables
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/courseflow"
export REDIS_HOST=localhost
export REDIS_PORT=6380
```

### API Usage

```bash
# Enroll student
curl -X POST http://localhost:8000/enroll \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": 123,
    "course_id": 1,
    "idempotency_key": "unique-key-123",
    "priority": 10
  }'

# Get metrics
curl http://localhost:8000/metrics
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/enroll` | POST | Submit enrollment request |
| `/metrics` | GET | System metrics |

## Test Results

```
============================= test session starts ==============================
platform linux -- Python 3.13.11, pytest-9.0.2, pluggy-1.6.0

tests/unit/test_allocator_logic.py::test_waitlist_when_full PASSED       [ 50%]
tests/unit/test_priority_score.py::test_priority_affects_score PASSED    [100%]
tests/integration/test_capacity.py::test_capacity_not_exceeded PASSED
tests/integration/test_concurrency.py::test_spike_stability PASSED
tests/integration/test_idempotency.py::test_idempotency_protection PASSED
tests/integration/test_priorty.py::test_priority_boost PASSED
tests/integration/test_waitlist.py::test_waitlist_behavior PASSED

============================== 7 passed in ~18s ===============================
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/courseflow` | Database connection |
| `REDIS_HOST` | `localhost` | Redis host |
| `REDIS_PORT` | `6379` | Redis port |
| `SERVER_PORT` | `8000` | HTTP server port |

## Metrics

Current metrics endpoint (`GET /metrics`):
```json
{
  "queue_depth": 0,
  "seats_taken": 5,
  "capacity": 10,
  "status": "operational"
}
```

## Logging

```
INFO:courseflow.allocator:Registered 1 in 0.0137s
INFO:courseflow.worker:Processed: success
```

## Future Work (v2.2+)

### Observability
- [ ] Prometheus metrics endpoint
- [ ] Structured JSON logging
- [ ] Distributed tracing (OpenTelemetry)
- [ ] Latency histograms (p50, p95, p99)

### Reliability
- [ ] Retry logic with exponential backoff
- [ ] Dead letter queue for failed processing
- [ ] Graceful shutdown (SIGTERM handling)
- [ ] Health check endpoints (`/health`, `/ready`)

### Scalability
- [ ] Horizontal worker scaling (Celery/RQ)
- [ ] Redis Cluster for HA
- [ ] Database read replicas

### Security
- [ ] Rate limiting
- [ ] JWT Authentication
- [ ] Input validation (Pydantic)

### API Improvements
- [ ] API versioning (`/api/v1/`)
- [ ] OpenAPI/Swagger docs
- [ ] WebSocket for real-time status

### Code Quality
- [ ] Type hints throughout
- [ ] Environment-based config
- [ ] Docker containerization
