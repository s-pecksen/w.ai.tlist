# Use Python 3.11 instead of 3.13 for better package compatibility
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies including PostgreSQL client
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create the data directory for any local storage needs
RUN mkdir -p /app/data \
    && chmod 755 /app/data

# Copy pyproject.toml and README.md first to leverage Docker cache
COPY pyproject.toml README.md ./

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Copy the rest of the application
COPY . .

# Set permissions for the application directory
# 755 for directories (drwxr-xr-x)
RUN find /app -type d -exec chmod 755 {} \; \
    # 644 for files (rw-r--r--)
    && find /app -type f -exec chmod 644 {} \; \
    # Make main.py executable
    && chmod 755 /app/main.py \
    # Set ownership
    && chown -R nobody:nogroup /app

# Create non-root user
USER nobody

# Expose the FastAPI app port
EXPOSE 8000

# Command to run the FastAPI app with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]