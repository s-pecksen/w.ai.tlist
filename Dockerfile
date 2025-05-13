# Use Python 3.9 as base image 
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy all files into the container
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Make port 7860 available
EXPOSE 7860

# Environment variable to use port 7860
ENV PORT=7860

# Start the application
CMD ["flask", "run", "--host=0.0.0.0", "--port=${PORT:-7860}"]