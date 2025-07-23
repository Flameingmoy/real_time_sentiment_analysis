# Sentiment Analysis Service Dockerfile

FROM python:3.11

WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code into container
COPY . .

# Expose 8000 to access the sentiment analysis service
EXPOSE 8000

# Placeholder command, to be replaced after the service is implemented
CMD ["python", "./validate_connections.py"]
