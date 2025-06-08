# Use an official Python image as the base
FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Create the persistent storage directory and set permissions
RUN mkdir -p /data/users \
    && mkdir -p /data/flask_sessions \
    && mkdir -p /data/diff_store \
    # Set base permissions for /data (drwxr-xr-x)
    && chmod 755 /data \
    # Set permissions for users directory (drwxrwxr-x)
    && chmod 775 /data/users \
    # Set permissions for flask_sessions (drwxrwxr-x)
    && chmod 775 /data/flask_sessions \
    # Set permissions for diff_store (drwxrwxr-x)
    && chmod 775 /data/diff_store \
    # Set ownership for all data directories
    && chmod -R 777 /data

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Make wait-for-db script executable
RUN chmod +x wait-for-db.sh

# Set permissions for the application directory
# 755 for directories (drwxr-xr-x)
RUN find /app -type d -exec chmod 755 {} \; \
    # 644 for files (rw-r--r--)
    && find /app -type f -exec chmod 644 {} \; \
    # Make app.py executable
    && chmod 755 /app/app.py \
    # Set ownership
    && chown -R nobody:nogroup /app

# Expose the Flask app port
EXPOSE 7860

# Command to run your app
CMD ["python", "app.py"]