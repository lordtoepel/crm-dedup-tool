FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for weasyprint
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --force-reinstall -r requirements.txt

# Copy application code
COPY . .

# Expose port (Railway sets $PORT dynamically)
EXPOSE 8000

# Run the application - use shell form so $PORT is expanded
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
