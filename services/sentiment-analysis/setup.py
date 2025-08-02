#!/usr/bin/env python3
"""
Setup script for sentiment analysis service
"""

import os
import subprocess
import sys
import asyncio
from pathlib import Path

def check_python_version():
    """Check Python version compatibility"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ is required")
        sys.exit(1)
    print("✅ Python version compatible")

def install_dependencies():
    """Install required dependencies"""
    print("📦 Installing dependencies...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                      check=True, capture_output=True, text=True)
        print("✅ Dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        sys.exit(1)

def create_directories():
    """Create necessary directories"""
    directories = [
        'logs',
        'data',
        'models',
        'cache'
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Created directory: {directory}")

def setup_environment():
    """Setup environment variables"""
    env_file = ".env"
    if not Path(env_file).exists():
        print("📋 Creating .env file...")
        with open(env_file, 'w') as f:
            f.write("""# Database Configuration
DB_HOST=localhost
DB_PORT=5433
DB_NAME=rtsa_analytics
DB_USER=rtsa_user
DB_PASSWORD=rtsa_password
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# Kafka Configuration
KAFKA_BROKERS=localhost:9092
KAFKA_GROUP_ID=sentiment-analysis-group
KAFKA_SENTIMENT_TOPIC=sentiment_analysis_topic
KAFKA_AGGREGATION_TOPIC=aggregation_topic
KAFKA_ALERT_TOPIC=alert_topic
KAFKA_AUTO_OFFSET_RESET=earliest
KAFKA_ENABLE_AUTO_COMMIT=true
KAFKA_MAX_POLL_RECORDS=100

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# Ollama Configuration
OLLAMA_HOST=localhost
OLLAMA_PORT=11434
OLLAMA_MODEL=granite3.3
OLLAMA_TIMEOUT=300
OLLAMA_MAX_RETRIES=3

# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
DEBUG=false
LOG_LEVEL=INFO
""")
        print("✅ Environment file created")
    else:
        print("✅ Environment file already exists")

def validate_connections():
    """Validate service connections"""
    print("🔍 Validating service connections...")
    try:
        from validate_connections import main as validate_main
        asyncio.run(validate_main())
    except Exception as e:
        print(f"❌ Connection validation failed: {e}")
        return False
    return True

def create_startup_script():
    """Create startup script"""
    startup_script = """#!/bin/bash
# Sentiment Analysis Service Startup Script

echo "🚀 Starting Sentiment Analysis Service..."

# Check if virtual environment is active
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  No virtual environment detected. Please activate your virtual environment."
    echo "   Run: source venv/bin/activate"
    exit 1
fi

# Load environment variables
if [[ -f .env ]]; then
    source .env
    echo "✅ Environment variables loaded"
else
    echo "❌ .env file not found"
    exit 1
fi

# Validate connections
echo "🔍 Validating connections..."
python validate_connections.py

if [[ $? -ne 0 ]]; then
    echo "❌ Connection validation failed"
    exit 1
fi

echo "✅ All connections validated successfully"

# Start the service
echo "🚀 Starting sentiment analysis service..."
python main.py
"""
    
    with open("start.sh", 'w') as f:
        f.write(startup_script)
    
    os.chmod("start.sh", 0o755)
    print("✅ Startup script created: start.sh")

def create_docker_compose():
    """Create Docker Compose configuration"""
    docker_compose = """version: '3.8'

services:
  sentiment-analysis:
    build: .
    container_name: rtsa-sentiment-analysis
    ports:
      - "8000:8000"
    environment:
      - DEBUG=false
      - LOG_LEVEL=INFO
    env_file:
      - .env
    depends_on:
      - postgres
      - redis
      - ollama
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
    restart: unless-stopped

  postgres:
    image: postgres:15
    container_name: rtsa-postgres
    ports:
      - "5433:5432"
    environment:
      - POSTGRES_DB=rtsa_analytics
      - POSTGRES_USER=rtsa_user
      - POSTGRES_PASSWORD=rtsa_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    container_name: rtsa-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

  ollama:
    image: ollama/ollama:latest
    container_name: rtsa-ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  ollama_data:
"""
    
    with open("docker-compose.yml", 'w') as f:
        f.write(docker_compose)
    
    print("✅ Docker Compose configuration created")

def create_dockerfile():
    """Create Dockerfile"""
    dockerfile = """FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    g++ \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs data models cache

# Set permissions
RUN chmod +x start.sh

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run the application
CMD ["python", "main.py"]
"""
    
    with open("Dockerfile", 'w') as f:
        f.write(dockerfile)
    
    print("✅ Dockerfile created")

def main():
    """Main setup function"""
    print("🚀 Setting up Sentiment Analysis Service...")
    
    check_python_version()
    install_dependencies()
    create_directories()
    setup_environment()
    create_startup_script()
    create_docker_compose()
    create_dockerfile()
    
    print("\n🎉 Setup complete!")
    print("\nNext steps:")
    print("1. Ensure all services are running (PostgreSQL, Redis, Kafka, Ollama)")
    print("2. Run: python validate_connections.py")
    print("3. Run: ./start.sh")
    print("4. Access health check at: http://localhost:8000/health")
    print("5. Access API documentation at: http://localhost:8000/docs")

if __name__ == "__main__":
    main()
