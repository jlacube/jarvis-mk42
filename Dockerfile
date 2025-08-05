# Multi-stage Dockerfile for JARVIS-MK42 Production Deployment
FROM python:3.9-slim as builder

# Set build arguments
ARG BUILDPLATFORM
ARG TARGETPLATFORM

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libssl-dev \
    libffi-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.9-slim as production

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    tesseract-ocr \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r jarvis && useradd -r -g jarvis jarvis

# Set working directory
WORKDIR /app

# Copy Python packages from builder stage
COPY --from=builder /root/.local /home/jarvis/.local

# Copy application code
COPY . .

# Set ownership and permissions
RUN chown -R jarvis:jarvis /app
USER jarvis

# Set Python path to include user packages
ENV PATH=/home/jarvis/.local/bin:$PATH
ENV PYTHONPATH=/app

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Expose ports
EXPOSE 8000 8001

# Default command
CMD ["python", "health_check.py"]
