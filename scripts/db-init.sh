#!/bin/bash

# Real-time Sentiment Analysis - Developer Database Initializer
# This script starts and verifies the PostgreSQL database services for development.

set -e

# --- Configuration ---
# Service names from docker-compose.yml
DB_SERVICES="psql-raw psql-analytics psql-logs"
WAIT_TIMEOUT="30s"

# --- Output Formatting ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARN]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo "Starting Developer Database Initialization..."

# --- Prerequisite Checks ---
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker first."
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    print_error "docker compose is not installed. Please install it first."
    exit 1
fi

# --- Main Logic ---
print_status "Starting PostgreSQL services: $DB_SERVICES..."
docker-compose up -d $DB_SERVICES

print_status "Waiting for databases to become healthy (max ${WAIT_TIMEOUT})..."

# Use docker-compose's native wait which relies on the healthcheck in the compose file
if docker-compose wait --timeout ${WAIT_TIMEOUT%s} $DB_SERVICES; then
    print_status "All databases are healthy!"
else
    print_error "One or more databases failed to become healthy within the timeout."
    print_warning "Check container logs with: docker-compose logs $DB_SERVICES"
    exit 1
fi

print_status "Database setup completed successfully!"