FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

ENV DATABASE_URL=postgresql://postgres:postgres@postgres:5432/courseflow
ENV REDIS_HOST=redis
ENV REDIS_PORT=6379
ENV SERVER_PORT=8000

CMD ["python", "-m", "courseflow.main"]
