FROM python:3.11-slim

ARG HOST_UID=1000
ARG HOST_GID=1000
ENV HOST_UID=${HOST_UID} \
    HOST_GID=${HOST_GID}

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Create directories for data and logs
RUN mkdir -p /app/data /app/logs

# Create non-root user with homedir at /app and set permissions
RUN groupadd -r -g ${HOST_GID:-1000} appuser && \
    useradd -r -s /bin/bash -u ${HOST_UID:-1000} -g appuser -d /app appuser
RUN chown -R appuser:appuser /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ app/

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Switch to non-root user
USER appuser
