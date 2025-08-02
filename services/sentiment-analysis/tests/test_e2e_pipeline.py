#!/usr/bin/env python3
"""End-to-end test for the data processing pipeline."""

import asyncio
import os
import time
import uuid
import hashlib
import json

import httpx
import psycopg2
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

INGESTION_URL = os.getenv('INGESTION_SERVICE_URL', 'http://localhost:8080/webhook/news')
DB_HOST = os.getenv('RAW_DB_HOST', 'localhost')
DB_PORT = os.getenv('RAW_DB_PORT', 5435)
DB_NAME = os.getenv('RAW_DB_NAME', 'rtsa_raw')
DB_USER = os.getenv('RAW_DB_USER', 'rtsa_user')
DB_PASSWORD = os.getenv('RAW_DB_PASSWORD', 'rtsa_password')

POLL_INTERVAL_SECONDS = 2
POLL_TIMEOUT_SECONDS = 30

def get_db_connection():
    """Establish a connection to the PostgreSQL database."""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

from datetime import datetime, timezone

def generate_test_data():
    """Generate a unique news article for testing that matches the Go NewsArticle struct."""
    # This is the payload that will be sent in the POST request.
    payload = {
        "id": str(uuid.uuid4()),
        "source": "test_e2e_pipeline",
        "headline": f"Test Headline {uuid.uuid4()}",
        "summary": f"Test article summary {uuid.uuid4()}",
        "url": f"http://example.com/news/{uuid.uuid4()}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # The Go service hashes the 'content' part of its message, which is a map
    # created from the incoming request payload. We must replicate that exactly.
    # This means sorting the keys of the payload dictionary before hashing.
    json_string_for_hash = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    content_hash = hashlib.sha256(json_string_for_hash.encode('utf-8')).hexdigest()

    return payload, content_hash

async def test_pipeline():
    """Run the end-to-end pipeline test."""
    print("Starting end-to-end pipeline test...")
    
    test_payload, content_hash = generate_test_data()
    print(f"Generated test data with content_hash: {content_hash}")

    # 1. Ingest data
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(INGESTION_URL, json=test_payload, timeout=10)
        
        if response.status_code == 202:
            print(f"Ingestion successful. Status code: {response.status_code}")
        else:
            print(f"--- Test Failed ---")
            print(f"Ingestion failed. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return

    except httpx.RequestError as e:
        print(f"--- Test Failed ---")
        print(f"Failed to connect to ingestion service: {e}")
        return

    # 2. Verify data in raw_data DB
    print("Polling raw data database for ingestion record...")
    start_time = time.time()
    record = None
    
    while time.time() - start_time < POLL_TIMEOUT_SECONDS:
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM raw_data WHERE content_hash = %s",
                    (content_hash,)
                )
                record = cur.fetchone()
            conn.close()
            
            if record:
                print("--- Test Passed ---")
                print(f"Record found in database: {record}")
                return

        except Exception as e:
            print(f"Database connection failed: {e}")

        print("Record not found yet. Retrying...")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)

    print("--- Test Failed ---")
    print(f"Timed out waiting for record with content_hash: {content_hash}")

if __name__ == "__main__":
    asyncio.run(test_pipeline())
