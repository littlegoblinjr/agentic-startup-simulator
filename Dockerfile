# Stage 1: Build Frontend
FROM node:18-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Backend & Final Image
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY app/ ./app/

# Copy built frontend from Stage 1 into 'static' folder
# (FastAPI main.py serves files from this directory)
COPY --from=frontend-builder /app/frontend/dist ./static

# Ensure logs directory exists at runtime
RUN mkdir -p logs

# Configure networking — Render injects $PORT (default 10000)
ENV PORT=10000
EXPOSE 10000

# Run with uvicorn directly — reads $PORT at container start
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
