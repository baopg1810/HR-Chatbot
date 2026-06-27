# ---- Stage 1: Build Frontend ----
FROM node:20-alpine AS frontend-builder

WORKDIR /app/fontend

COPY fontend/package*.json ./
RUN npm install --prefer-offline --no-audit

COPY fontend/ ./
RUN npm run build

# ---- Stage 2: Build Python dependencies ----
FROM python:3.11-slim AS backend-builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ---- Stage 3: Production ----
FROM python:3.11-slim

WORKDIR /app

# Copy python dependencies
COPY --from=backend-builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app/backend

# Copy application files
COPY . .

# Copy built frontend from Stage 1
COPY --from=frontend-builder /app/fontend/dist ./fontend/dist

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import urllib.request, os; port = os.environ.get('PORT', '8000'); urllib.request.urlopen(f'http://localhost:{port}/health')" || exit 1

CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

