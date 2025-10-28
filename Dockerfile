# ===============================
# 1. Base image
# ===============================
FROM python:3.12

# ===============================
# 2. Environment setup
# ===============================
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies (for asyncpg, psycopg2, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# ===============================
# 3. Install Python dependencies
# ===============================
# Copy requirements first for better caching
COPY requirements.txt .

RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# ===============================
# 4. Copy project files
# ===============================
COPY . .

# Copy .env file (optional: it can be mounted instead)
COPY .env .env

# ===============================
# 5. Expose port & define entrypoint
# ===============================
EXPOSE 8000

# Optional: run Alembic migrations automatically at startup
# You can remove this if you prefer manual control
CMD alembic upgrade head && \
    gunicorn -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000 --workers 4
