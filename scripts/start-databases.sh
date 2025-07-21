#!/bin/bash

# Real-time Sentiment Analysis - Database Setup Script
# This script starts all PostgreSQL databases with proper configuration

set -e

echo "🚀 Starting Real-time Sentiment Analysis Database Setup..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker first."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker compose &> /dev/null; then
    print_error "docker-compose is not installed. Please install docker-compose first."
    exit 1
fi

print_status "Starting PostgreSQL databases..."

# Start the databases
docker-compose up -d postgres-raw postgres-analytics postgres-logging

print_status "Waiting for databases to be ready..."

# Wait for databases to be healthy
max_attempts=30
attempt=0

check_database() {
    local container_name=$1
    local db_name=$2
    local port=$3
    
    while [ $attempt -lt $max_attempts ]; do
        if docker exec $container_name pg_isready -U rtsa_user -d $db_name > /dev/null 2>&1; then
            print_status "$db_name database is ready on port $port"
            return 0
        fi
        
        attempt=$((attempt + 1))
        print_warning "Waiting for $db_name database... (attempt $attempt/$max_attempts)"
        sleep 2
    done
    
    print_error "$db_name database failed to start after $max_attempts attempts"
    return 1
}

# Check each database
check_database "rtsa-postgres-raw" "rtsa_raw" "5435"
check_database "rtsa-postgres-analytics" "rtsa_analytics" "5433"
check_database "rtsa-postgres-logging" "rtsa_logging" "5434"

print_status "All databases are ready!"

# Display connection information
echo ""
echo "📊 Database Connection Information:"
echo "=================================="
echo "Raw Data Database:"
echo "  Host: localhost"
echo "  Port: 5435"
echo "  Database: rtsa_raw"
echo "  User: rtsa_user"
echo "  Password: rtsa_password"
echo ""
echo "Analytics Database:"
echo "  Host: localhost"
echo "  Port: 5433"
echo "  Database: rtsa_analytics"
echo "  User: rtsa_user"
echo "  Password: rtsa_password"
echo ""
echo "Logging Database:"
echo "  Host: localhost"
echo "  Port: 5434"
echo "  Database: rtsa_logging"
echo "  User: rtsa_user"
echo "  Password: rtsa_password"
echo ""

print_status "Database setup completed successfully! 🎉"