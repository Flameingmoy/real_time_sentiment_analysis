#!/usr/bin/env python3
"""
Environment Setup Validation Script
Validates all service connections for the RTSA system
"""

import os
import sys
import time
import requests
import psycopg2
import redis
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
import subprocess
import json

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_status(service, status, message=""):
    color = Colors.GREEN if status == "OK" else Colors.RED if status == "FAIL" else Colors.YELLOW
    print(f"{color}[{status}]{Colors.ENDC} {service}: {message}")

def check_go_environment():
    """Check Go development environment"""
    print(f"\n{Colors.BOLD}=== Go Development Environment ==={Colors.ENDC}")
    
    try:
        # Check Go version
        result = subprocess.run(['go', 'version'], capture_output=True, text=True)
        if result.returncode == 0:
            print_status("Go Installation", "OK", result.stdout.strip())
        else:
            print_status("Go Installation", "FAIL", "Go not found")
            return False
            
        # Check Go modules in ingestion service
        os.chdir('services/ingestion')
        result = subprocess.run(['go', 'mod', 'verify'], capture_output=True, text=True)
        if result.returncode == 0:
            print_status("Go Modules (Ingestion)", "OK", "All modules verified")
        else:
            print_status("Go Modules (Ingestion)", "FAIL", result.stderr)
            
        # Check required packages
        required_packages = ['github.com/gin-gonic/gin', 'github.com/jackc/pgx/v5', 'github.com/IBM/sarama']
        with open('go.mod', 'r') as f:
            go_mod_content = f.read()
            
        for package in required_packages:
            if package in go_mod_content:
                print_status(f"Package {package}", "OK", "Found in go.mod")
            else:
                print_status(f"Package {package}", "FAIL", "Missing from go.mod")
                
        os.chdir('../..')
        return True
        
    except Exception as e:
        print_status("Go Environment", "FAIL", str(e))
        return False

def check_python_environment():
    """Check Python development environment"""
    print(f"\n{Colors.BOLD}=== Python Development Environment ==={Colors.ENDC}")
    
    try:
        # Check Python version
        python_version = sys.version
        print_status("Python Installation", "OK", f"Python {python_version.split()[0]}")
        
        # Check required packages
        required_packages = {
            'kafka': 'kafka-python',
            'psycopg2': 'psycopg2-binary', 
            'ollama': 'ollama',
            'fastapi': 'fastapi',
            'redis': 'redis'
        }
        
        for import_name, package_name in required_packages.items():
            try:
                __import__(import_name)
                print_status(f"Package {package_name}", "OK", "Installed and importable")
            except ImportError:
                print_status(f"Package {package_name}", "FAIL", "Not installed or not importable")
                
        return True
        
    except Exception as e:
        print_status("Python Environment", "FAIL", str(e))
        return False

def check_ollama():
    """Check Ollama installation and Granite model"""
    print(f"\n{Colors.BOLD}=== Ollama and Granite Model ==={Colors.ENDC}")
    
    try:
        # Check if Ollama is running
        response = requests.get('http://localhost:11434/api/tags', timeout=5)
        if response.status_code == 200:
            print_status("Ollama Service", "OK", "Running on localhost:11434")
            
            # Check for Granite models
            models = response.json().get('models', [])
            granite_models = [model for model in models if 'granite' in model.get('name', '').lower()]
            
            if granite_models:
                for model in granite_models:
                    print_status("Granite Model", "OK", f"Found: {model['name']}")
            else:
                print_status("Granite Model", "WARN", "No Granite models found. You may need to pull granite3-dense:2b or granite3-dense:8b")
                
        else:
            print_status("Ollama Service", "FAIL", f"HTTP {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print_status("Ollama Service", "FAIL", "Connection refused - Ollama may not be running")
    except Exception as e:
        print_status("Ollama Service", "FAIL", str(e))

def check_postgresql_connections():
    """Check PostgreSQL database connections"""
    print(f"\n{Colors.BOLD}=== PostgreSQL Databases ==={Colors.ENDC}")
    
    databases = [
        {"name": "Raw Data", "host": "localhost", "port": 5435, "db": "rtsa_raw"},
        {"name": "Analytics", "host": "localhost", "port": 5433, "db": "rtsa_analytics"},
        {"name": "Logging", "host": "localhost", "port": 5434, "db": "rtsa_logging"}
    ]
    
    for db_config in databases:
        try:
            conn = psycopg2.connect(
                host=db_config["host"],
                port=db_config["port"],
                database=db_config["db"],
                user="rtsa_user",
                password="rtsa_password"
            )
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            print_status(f"PostgreSQL {db_config['name']}", "OK", f"Connected - {version.split()[0]} {version.split()[1]}")
            conn.close()
            
        except Exception as e:
            print_status(f"PostgreSQL {db_config['name']}", "FAIL", str(e))

def check_kafka():
    """Check Kafka connection"""
    print(f"\n{Colors.BOLD}=== Apache Kafka ==={Colors.ENDC}")
    
    try:
        # Test Kafka producer
        producer = KafkaProducer(
            bootstrap_servers=['localhost:9092'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        
        # Send test message
        future = producer.send('test_topic', {'test': 'message'})
        producer.flush()
        print_status("Kafka Producer", "OK", "Successfully sent test message")
        
        # Test Kafka consumer
        consumer = KafkaConsumer(
            'test_topic',
            bootstrap_servers=['localhost:9092'],
            auto_offset_reset='latest',
            consumer_timeout_ms=1000
        )
        print_status("Kafka Consumer", "OK", "Successfully created consumer")
        consumer.close()
        producer.close()
        
    except Exception as e:
        print_status("Kafka", "FAIL", str(e))

def check_redis():
    """Check Redis connection"""
    print(f"\n{Colors.BOLD}=== Redis Vector Store ==={Colors.ENDC}")
    
    try:
        r = redis.Redis(host='localhost', port=6380, decode_responses=True)
        r.ping()
        print_status("Redis Connection", "OK", "Successfully connected")
        
        # Check RedisSearch module
        modules = r.execute_command('MODULE', 'LIST')
        search_module = any('search' in str(module).lower() for module in modules)
        if search_module:
            print_status("RedisSearch Module", "OK", "Module loaded")
        else:
            print_status("RedisSearch Module", "WARN", "Module not found")
            
    except Exception as e:
        print_status("Redis", "FAIL", str(e))

def check_grafana():
    """Check Grafana connection and data sources"""
    print(f"\n{Colors.BOLD}=== Grafana Dashboard ==={Colors.ENDC}")
    
    try:
        # Check Grafana health
        response = requests.get('http://localhost:3000/api/health', timeout=10)
        if response.status_code == 200:
            print_status("Grafana Service", "OK", "Running on localhost:3000")
            
            # Check data sources (requires authentication)
            auth = ('admin', 'admin')
            ds_response = requests.get('http://localhost:3000/api/datasources', auth=auth, timeout=10)
            
            if ds_response.status_code == 200:
                datasources = ds_response.json()
                expected_sources = ['RTSA Analytics', 'RTSA Logging', 'RTSA Raw Data']
                
                for expected in expected_sources:
                    found = any(ds['name'] == expected for ds in datasources)
                    if found:
                        print_status(f"Data Source: {expected}", "OK", "Configured")
                    else:
                        print_status(f"Data Source: {expected}", "FAIL", "Not found")
            else:
                print_status("Grafana Data Sources", "WARN", f"Could not check data sources (HTTP {ds_response.status_code})")
                
        else:
            print_status("Grafana Service", "FAIL", f"HTTP {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print_status("Grafana Service", "FAIL", "Connection refused - Grafana may not be running")
    except Exception as e:
        print_status("Grafana Service", "FAIL", str(e))

def main():
    print(f"{Colors.BOLD}Real-time Sentiment Analysis - Environment Validation{Colors.ENDC}")
    print("=" * 60)
    
    # Run all checks
    check_go_environment()
    check_python_environment()
    check_ollama()
    check_postgresql_connections()
    check_kafka()
    check_redis()
    check_grafana()
    
    print(f"\n{Colors.BOLD}=== Validation Complete ==={Colors.ENDC}")
    print("If any services show FAIL status, ensure they are running with: docker compose up -d")

if __name__ == "__main__":
    main()