# ---- Stage 1: Python dependencies ----
FROM python:3.11-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ---- Stage 2: Frontend build ----
FROM node:20-slim AS frontend_builder

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ---- Stage 3: Production ----
FROM python:3.11-slim

WORKDIR /app

# Copy installed Python packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application source code
COPY backend/ ./backend/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Copy frontend build output
COPY --from=frontend_builder /app/frontend/dist ./frontend/dist

# Create data directory for ChromaDB persistence
RUN mkdir -p /app/data

# Railway injects PORT env var; default to 8000 for local dev
ENV PORT=8000
ENV PYTHONPATH=/app/backend:$PYTHONPATH
ENV PYTHONUNBUFFERED=1

EXPOSE ${PORT}

# Use shell form so $PORT is expanded at runtime
CMD sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT"
