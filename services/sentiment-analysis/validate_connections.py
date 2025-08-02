#!/usr/bin/env python3

import os
import sys
import asyncio
import psycopg2
import redis
import ollama
from kafka import KafkaProducer, KafkaConsumer
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_postgresql_connections():
    """Test PostgreSQL database connections"""
    databases = [
        {
            'name': 'Analytics DB',
            'host': os.getenv('ANALYTICS_DB_HOST'),
            'port': os.getenv('ANALYTICS_DB_PORT'),
            'database': os.getenv('ANALYTICS_DB_NAME'),
            'user': os.getenv('ANALYTICS_DB_USER'),
            'password': os.getenv('ANALYTICS_DB_PASSWORD')
        },
        {
            'name': 'Logging DB',
            'host': os.getenv('LOGGING_DB_HOST'),
            'port': os.getenv('LOGGING_DB_PORT'),
            'database': os.getenv('LOGGING_DB_NAME'),
            'user': os.getenv('LOGGING_DB_USER'),
            'password': os.getenv('LOGGING_DB_PASSWORD')
        }
    ]
    
    for db_config in databases:
        print(f"📊 Testing {db_config['name']} connection... ", end="")
        try:
            conn = psycopg2.connect(
                host=db_config['host'],
                port=db_config['port'],
                database=db_config['database'],
                user=db_config['user'],
                password=db_config['password']
            )
            cursor = conn.cursor()
            cursor.execute("SELECT 'PostgreSQL connection successful'")
            result = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            print(f"✅ {result}")
        except Exception as e:
            print(f"❌ Failed: {e}")

def test_kafka_connection():
    """Test Kafka connection"""
    print("📨 Testing Kafka connection... ", end="")
    try:
        brokers = os.getenv('KAFKA_BROKERS').split(',')
        producer = KafkaProducer(
            bootstrap_servers=brokers,
            request_timeout_ms=10000,
            api_version=(2, 8, 0)
        )
        producer.close()
        print("✅ Kafka connection successful")
    except Exception as e:
        print(f"❌ Failed: {e}")

def test_redis_connection():
    """Test Redis connection"""
    print("🔴 Testing Redis connection... ", end="")
    try:
        r = redis.Redis(
            host=os.getenv('REDIS_HOST'),
            port=int(os.getenv('REDIS_PORT')),
            db=int(os.getenv('REDIS_DB')),
            socket_timeout=10
        )
        r.ping()
        print("✅ Redis connection successful")
    except Exception as e:
        print(f"❌ Failed: {e}")

def test_ollama_connection():
    """Test Ollama connection"""
    print("🤖 Testing Ollama connection... ", end="")
    try:
        client = ollama.Client(host=os.getenv('OLLAMA_HOST'))
        models = client.list()
        model_name = "granite3.3:8b"
        
        # Check if the required model is available
        available_models = [model['name'] for model in models['models']]
        if model_name in available_models:
            print(f"✅ Ollama connected, {model_name} model available")
        else:
            print(f"⚠️  Ollama connected, but {model_name} model not found")
            print(f"   Available models: {', '.join(available_models)}")
    except Exception as e:
        print(f"❌ Failed: {e}")

async def main():
    """Main validation function"""
    print("🔍 Validating service connections...")
    
    await test_postgresql_connections()
    test_kafka_connection()
    test_redis_connection()
    test_ollama_connection()
    
    print("🎉 Connection validation complete!")

if __name__ == "__main__":
    asyncio.run(main())