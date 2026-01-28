FROM python:3.11-slim

WORKDIR /app

# Set environment variables for UTF-8
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PYTHONIOENCODING=utf-8

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY *.py .
COPY pp2_rules.txt .
COPY config.yaml .
COPY models/ ./models/

# Create data directory
RUN mkdir -p /app/data

# Run the detector
CMD ["python", "-u", "detector.py"]
