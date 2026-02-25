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
- **Health Checks**: `/health` and `/ready` endpoints
- **Graceful Shutdown**: Worker stops cleanly on SIGTERM
- **Multi-course**: Support for multiple courses via `/courses` endpoint
- **Docker Ready**: Dockerfile and docker-compose included

## Quick Start

### Option 1: Docker Compose (Recommended)

```bash
# Clone and run
docker-compose up --build

# Check health
curl http://localhost:8000/health
```

### Option 2: Manual

```bash
# Run PostgreSQL (port 5432)
docker run -d --name postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=courseflow \
  -p 5432:5432 postgres

# Run Redis (port 6380)
docker run -d --name redis \
  -p 6380:6379 redis

# Set environment variables
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/courseflow"
export REDIS_HOST=localhost
export REDIS_PORT=6380

# Install & run
pip install -r requirements.txt
python -m courseflow.main
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Liveness probe |
| `/ready` | GET | Readiness probe (checks Redis + DB) |
| `/enroll` | POST | Submit enrollment request |
| `/metrics` | GET | System metrics (supports `?course_id=1`) |
| `/courses` | GET | List all courses |

### API Usage

```bash
# Check health
curl http://localhost:8000/health

# Check readiness
curl http://localhost:8000/ready

# List courses
curl http://localhost:8000/courses

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
curl http://localhost:8000/metrics?course_id=1
```

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

```json
{
  "course_id": 1,
  "queue_depth": 0,
  "seats_taken": 5,
  "capacity": 10,
  "status": "operational"
}
```

## Future Work

- [ ] Prometheus metrics endpoint
- [ ] JWT Authentication
- [ ] Rate limiting
- [ ] WebSocket for real-time status
- [ ] API versioning (`/api/v1/`)
