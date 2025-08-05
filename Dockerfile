FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including sqlite3 and ffmpeg
RUN apt-get update && apt-get install -y \
    sqlite3 \
    libsqlite3-dev \
    ffmpeg \
    && echo "Dependencies installed OK" \
    || (echo "Failed to install dependencies" && exit 1)

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

EXPOSE 8000

# Start app
CMD ["gunicorn", "--workers", "2", "--worker-class", "uvicorn.workers.UvicornWorker","--timeout", "24000", "--bind", "0.0.0.0:8000", "api:app"]

