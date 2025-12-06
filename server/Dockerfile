
# Use Python 3.10 slim image for a smaller footprint
FROM python:3.10-slim

# Set working directory inside the container
WORKDIR /app

# Install system dependencies required for pdf2image and other potential tools
RUN apt-get update && apt-get install -y \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire server application code
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
# Using host 0.0.0.0 is crucial for Docker networking
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
