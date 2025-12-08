FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY mvp/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY mvp/ .

# Create data directory for SQLite
RUN mkdir -p /app/data

# Environment
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:${PORT}/health')" || exit 1

# Run the API
CMD ["python", "api.py"]
