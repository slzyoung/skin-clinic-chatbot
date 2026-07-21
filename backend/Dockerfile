# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends gcc build-essential && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Development
FROM python:3.11-slim AS development

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY . .

RUN chmod +x /app/start.sh
RUN mkdir -p data/temp logs

EXPOSE 8000

# Run in development mode (with hot reload)
CMD ["/app/start.sh", "dev"]

# Stage 3: Production
FROM python:3.11-slim AS production

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY . .

RUN chmod +x /app/start.sh
RUN mkdir -p data/temp logs

EXPOSE 8000

# Run in production mode
CMD ["/app/start.sh", "prod"]
