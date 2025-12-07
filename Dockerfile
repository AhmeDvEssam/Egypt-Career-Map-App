# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port (Fly.io will set PORT env var)
EXPOSE 8080

# Set default PORT if not provided
ENV PORT=8080

# Run with waitress
CMD ["sh", "-c", "waitress-serve --host=0.0.0.0 --port=$PORT --threads=6 --channel-timeout=60 index:server"]
