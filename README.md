# CourseFlow - Distributed Course Enrollment Engine

A deterministic, concurrency-safe course allocation system built with FastAPI, Redis, and PostgreSQL.

## Problem

Course enrollment is a **deterministic allocation problem**, not CRUD. When 500 students compete for 30 seats:
- Race conditions must not corrupt invariants
- Duplicate submissions must be idempotent
- Priority must be respected fairly
- Capacity must never be exceeded

CourseFlow solves this with a **separation of arbitration and allocation**.

## Architecture

```
                    ┌─────────────────┐
                    │   FastAPI API    │  ← Arbitration Layer
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Redis Sorted   │  ← Priority Arbitration
                    │      Set        │    (score = time - priority)
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Async Worker   │  ← Allocation Engine
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
        ┌─────▼─────┐ ┌──────▼──────┐ ┌────▼────────┐
        │ PostgreSQL │ │  Enrollment │ │   Waitlist │
        │   Course   │ │    Table    │ │    Table   │
        └───────────┘ └─────────────┘ └─────────────┘
```

**Separation of Concerns:**
- **Arbitration (API)**: Fast, stateless, accepts or rejects immediately
- **Allocation (Worker)**: Slow, correct, enforces invariants transactionally

## System Guarantees

### Invariants (Never Violated)

| Invariant | Mechanism |
|-----------|-----------|
| `seats_taken ≤ capacity` | `SELECT FOR UPDATE` row lock |
| No duplicate enrollments | Unique `idempotency_key` constraint |
| No race conditions | Database transaction + row locking |
| No lost updates | Serialized course capacity access |

### Concurrency Properties

| Property | Guarantee |
|----------|-----------|
| **Linearizability** | Each enrollment is processed exactly once |
| **Isolation** | `SELECT FOR UPDATE` prevents dirty reads |
| **Atomicity** | Full transaction rollback on failure |
| **Idempotency** | Duplicate `idempotency_key` returns success |

## Concurrency Validation

The test suite validates concurrency correctness:

```
tests/integration/test_concurrency.py::test_spike_stability PASSED
tests/integration/test_capacity.py::test_capacity_not_exceeded PASSED
tests/integration/test_idempotency.py::test_idempotency_protection PASSED
tests/unit/test_allocator_logic.py::test_waitlist_when_full PASSED

7 passed, 0 race conditions detected
```

## Key Components

### Redis Sorted Set (Arbitration)

```python
# Score = timestamp (earlier = higher priority) - priority boost
score = (time.time() * 1_000_000) - (priority * 10_000)
r.zadd(queue_key, {payload: score})
```

Why sorted sets?
- O(log N) insertion
- O(log N) priority updates  
- Automatic ordering by score
- Atomic `ZPOPMIN` for lowest-score extraction

### PostgreSQL (Allocation)

```python
with db.begin():
    course = db.query(Course).filter(...).with_for_update().first()
    # Row is now locked until transaction commits
    
    if course.seats_taken >= course.capacity:
        db.add(Waitlist(...))
        return {"status": "waitlisted"}
    
    course.seats_taken += 1
    db.add(Enrollment(...))
```

Why `SELECT FOR UPDATE`?
- Prevents two workers from reading same `seats_taken`
- Serializes access to course capacity
- Ensures deterministic outcome under contention

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Liveness probe |
| `/ready` | GET | Readiness (Redis + DB connectivity) |
| `/enroll` | POST | Submit enrollment request |
| `/metrics` | GET | Prometheus metrics (Prometheus format) |
| `/metrics/json` | GET | Application metrics (JSON format) |
| `/courses` | GET | List courses |

## Prometheus Metrics

```bash
# Scrape metrics for Prometheus
curl http://localhost:8000/metrics

# Or get JSON format
curl http://localhost:8000/metrics/json
```

Available metrics:
- `enrollment_requests_total` - Total enrollment requests by status
- `enrollment_latency_seconds` - Enrollment processing latency histogram
- `courseflow_queue_depth` - Current queue depth per course
- `courseflow_seats_taken` - Seats taken per course
- `courseflow_capacity` - Course capacity

## Health & Lifecycle

### Health Checks

```bash
# Liveness - is process running?
curl http://localhost:8000/health
# {"status": "ok"}

# Readiness - are dependencies available?
curl http://localhost:8000/ready
# {"status": "ready", "redis": "ok", "database": "ok"}
```

### Graceful Shutdown

On SIGTERM:
1. API stops accepting new requests
2. Worker finishes current enrollment
3. In-flight transactions complete
4. Process exits cleanly

No enrollment is lost mid-transaction.

## Deployment

### Docker Compose

```bash
docker-compose up --build
```

### Manual

```bash
# Dependencies
docker run -d -p 5432:5432 postgres:15
docker run -d -p 6379:6379 redis:7

# Run
export DATABASE_URL="postgresql://..."
export REDIS_HOST=localhost
export REDIS_PORT=6379
python -m courseflow.main
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://...` | PostgreSQL connection |
| `REDIS_HOST` | `localhost` | Redis host |
| `REDIS_PORT` | `6379` | Redis port |
| `SERVER_PORT` | `8000` | HTTP port |

## Why This Architecture

| Requirement | Solution |
|-------------|----------|
| High throughput API | Redis is O(1) for enqueue |
| Correct under concurrency | `SELECT FOR UPDATE` + transactions |
| Deterministic ordering | Redis sorted set by timestamp |
| No duplicate processing | Idempotency keys with DB constraint |
| Graceful degradation | Waitlist when capacity exceeded |
| Production ready | Health checks, graceful shutdown |

## Future Work

- [x] Prometheus metrics
- [ ] Multi-region replication
- [ ] WebSocket notifications for waitlist advancement
- [ ] Dead letter queue for failed enrollments
