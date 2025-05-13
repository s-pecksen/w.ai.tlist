# Use an official Python image as the base
FROM python:3.13-slim

# Set environment variables (optional, but good practice)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies (optional, but good for some packages)
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Create the persistent storage directory and set permissions
RUN mkdir -p /data \
 && chown -R 1000:1000 /data \
 && chmod -R 777 /data

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose the Flask app port
EXPOSE 7860

# Command to run your app
CMD ["python", "app.py"]