# ============================================================================
# EduPulse — Containerized Backend & Mobile Frontend
# ============================================================================
FROM python:3.13-slim

WORKDIR /app

# Prevent Python from writing .pyc and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libfreetype6-dev \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY supabase/ ./supabase/
COPY uploads/ ./uploads/
COPY run.py .

# Initialize database
RUN python -c "import sys; sys.path.append('backend'); from database import init_db, seed_demo_data; init_db(); seed_demo_data(reset=False)"

# Expose port (default 8000)
EXPOSE 8000
ENV PORT=8000

# Start server
CMD ["sh", "-c", "uvicorn backend.app:app --host 0.0.0.0 --port ${PORT}"]
