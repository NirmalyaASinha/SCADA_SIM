FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose ports (will be overridden by docker-compose)
EXPOSE 8101 8102 5020

# Run the node service
CMD ["python", "main.py"]
