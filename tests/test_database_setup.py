#!/usr/bin/env python3
"""
Real-time Sentiment Analysis - Database Setup Test
This script tests all three PostgreSQL database connections and validates schema setup.
"""

import psycopg2
import psycopg2.extras
import sys
import time
from datetime import datetime, timezone
import json

# Database configurations
DATABASES = {
    'raw': {
        'host': 'localhost',
        'port': 5435,
        'database': 'rtsa_raw',
        'user': 'rtsa_user',
        'password': 'rtsa_password'
    },
    'analytics': {
        'host': 'localhost',
        'port': 5433,
        'database': 'rtsa_analytics',
        'user': 'rtsa_user',
        'password': 'rtsa_password'
    },
    'logging': {
        'host': 'localhost',
        'port': 5434,
        'database': 'rtsa_logging',
        'user': 'rtsa_user',
        'password': 'rtsa_password'
    }
}

def print_status(message, status="INFO"):
    colors = {
        "INFO": "\033[0;32m",
        "WARN": "\033[1;33m", 
        "ERROR": "\033[0;31m",
        "SUCCESS": "\033[0;36m"
    }
    reset = "\033[0m"
    print(f"{colors.get(status, '')}[{status}]{reset} {message}")

def test_connection(db_name, config):
    """Test database connection and return connection object"""
    try:
        print_status(f"Testing connection to {db_name} database...")
        conn = psycopg2.connect(**config)
        conn.autocommit = True
        print_status(f"✅ Connected to {db_name} database successfully", "SUCCESS")
        return conn
    except Exception as e:
        print_status(f"❌ Failed to connect to {db_name} database: {e}", "ERROR")
        return None

def test_raw_database(conn):
    """Test raw database schema and functionality"""
    print_status("Testing raw database schema...")
    
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Test table exists
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'raw_data'
        """)
        if not cursor.fetchone():
            raise Exception("raw_data table not found")
        
        # Test partitioning function
        cursor.execute("SELECT create_monthly_partition('raw_data', CURRENT_DATE)")
        
        # Test data insertion
        test_data = {
            'source': 'test_source',
            'source_id': 'test_123',
            'content': {'message': 'Test message', 'value': 42},
            'timestamp': datetime.now(timezone.utc),
            'content_hash': 'test_hash_' + str(int(time.time()))
        }
        
        cursor.execute("""
            INSERT INTO raw_data (source, source_id, content, timestamp, content_hash)
            VALUES (%(source)s, %(source_id)s, %(content)s, %(timestamp)s, %(content_hash)s)
            RETURNING id
        """, test_data)
        
        result = cursor.fetchone()
        if result:
            print_status(f"✅ Successfully inserted test record with ID: {result['id']}", "SUCCESS")
        
        # Test indexes
        cursor.execute("""
            SELECT indexname FROM pg_indexes 
            WHERE tablename = 'raw_data' AND schemaname = 'public'
        """)
        indexes = [row[0] for row in cursor.fetchall()]
        expected_indexes = ['idx_raw_data_timestamp', 'idx_raw_data_source', 'idx_raw_data_content_hash']
        
        for idx in expected_indexes:
            if idx in indexes:
                print_status(f"✅ Index {idx} exists", "SUCCESS")
            else:
                print_status(f"❌ Index {idx} missing", "ERROR")
        
        # Test cleanup function
        cursor.execute("SELECT cleanup_old_raw_data()")
        print_status("✅ Cleanup function works", "SUCCESS")
        
        cursor.close()
        return True
        
    except Exception as e:
        print_status(f"❌ Raw database test failed: {e}", "ERROR")
        return False

def test_analytics_database(conn):
    """Test analytics database schema and functionality"""
    print_status("Testing analytics database schema...")
    
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Test main table exists
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'sentiment_results'
        """)
        if not cursor.fetchone():
            raise Exception("sentiment_results table not found")
        
        # Test materialized views
        views = ['hourly_sentiment_summary', 'daily_sentiment_summary', 'source_volume_metrics']
        for view in views:
            cursor.execute(f"""
                SELECT matviewname FROM pg_matviews 
                WHERE matviewname = '{view}' AND schemaname = 'public'
            """)
            if cursor.fetchone():
                print_status(f"✅ Materialized view {view} exists", "SUCCESS")
            else:
                print_status(f"❌ Materialized view {view} missing", "ERROR")
        
        # Test data insertion
        test_sentiment = {
            'source_id': 'test_source_123',
            'content_hash': 'test_sentiment_hash_' + str(int(time.time())),
            'timestamp': datetime.now(timezone.utc),
            'source_type': 'news',
            'content': 'This is a positive test message about the market.',
            'sentiment_score': 0.75,
            'sentiment_label': 'positive',
            'confidence_score': 0.85,
            'entities': {'companies': ['AAPL', 'GOOGL'], 'sentiment_keywords': ['positive', 'growth']},
            'metadata': {'model_version': 'granite-3.3-2b', 'processing_time': 2.5}
        }
        
        cursor.execute("""
            INSERT INTO sentiment_results 
            (source_id, content_hash, timestamp, source_type, content, sentiment_score, 
             sentiment_label, confidence_score, entities, metadata)
            VALUES (%(source_id)s, %(content_hash)s, %(timestamp)s, %(source_type)s, 
                    %(content)s, %(sentiment_score)s, %(sentiment_label)s, %(confidence_score)s,
                    %(entities)s, %(metadata)s)
            RETURNING id
        """, test_sentiment)
        
        result = cursor.fetchone()
        if result:
            print_status(f"✅ Successfully inserted sentiment record with ID: {result['id']}", "SUCCESS")
        
        # Test refresh function
        cursor.execute("SELECT refresh_sentiment_views()")
        print_status("✅ Materialized view refresh function works", "SUCCESS")
        
        # Test entity summary table
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'entity_summary'
        """)
        if cursor.fetchone():
            print_status("✅ Entity summary table exists", "SUCCESS")
        
        cursor.close()
        return True
        
    except Exception as e:
        print_status(f"❌ Analytics database test failed: {e}", "ERROR")
        return False

def test_logging_database(conn):
    """Test logging database schema and functionality"""
    print_status("Testing logging database schema...")
    
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Test main table exists
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'system_logs'
        """)
        if not cursor.fetchone():
            raise Exception("system_logs table not found")
        
        # Test partitioning function
        cursor.execute("SELECT create_daily_log_partition('system_logs', CURRENT_DATE)")
        print_status("✅ Daily partition creation function works", "SUCCESS")
        
        # Test log insertion
        test_log = {
            'level': 'INFO',
            'component': 'test_component',
            'message': 'This is a test log message',
            'metadata': {'test_key': 'test_value', 'timestamp': str(datetime.now())},
            'timestamp': datetime.now(timezone.utc)
        }
        
        cursor.execute("""
            INSERT INTO system_logs (level, component, message, metadata, timestamp)
            VALUES (%(level)s, %(component)s, %(message)s, %(metadata)s, %(timestamp)s)
            RETURNING id
        """, test_log)
        
        result = cursor.fetchone()
        if result:
            print_status(f"✅ Successfully inserted log record with ID: {result['id']}", "SUCCESS")
        
        # Test error summary table
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'error_summary'
        """)
        if cursor.fetchone():
            print_status("✅ Error summary table exists", "SUCCESS")
        
        # Test error summary function
        cursor.execute("""
            SELECT update_error_summary('test_component', 'test_error', 'Test error message')
        """)
        print_status("✅ Error summary update function works", "SUCCESS")
        
        # Test performance metrics table
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'performance_metrics'
        """)
        if cursor.fetchone():
            print_status("✅ Performance metrics table exists", "SUCCESS")
        
        # Test recent errors view
        cursor.execute("SELECT * FROM recent_errors LIMIT 1")
        print_status("✅ Recent errors view works", "SUCCESS")
        
        cursor.close()
        return True
        
    except Exception as e:
        print_status(f"❌ Logging database test failed: {e}", "ERROR")
        return False

def test_connection_pooling():
    """Test connection pooling capabilities"""
    print_status("Testing connection pooling...")
    
    try:
        # Test multiple concurrent connections
        connections = []
        for i in range(5):
            conn = psycopg2.connect(**DATABASES['analytics'])
            connections.append(conn)
        
        print_status(f"✅ Successfully created {len(connections)} concurrent connections", "SUCCESS")
        
        # Close all connections
        for conn in connections:
            conn.close()
        
        print_status("✅ Connection pooling test passed", "SUCCESS")
        return True
        
    except Exception as e:
        print_status(f"❌ Connection pooling test failed: {e}", "ERROR")
        return False

def main():
    """Main test function"""
    print_status("🧪 Starting Real-time Sentiment Analysis Database Tests...")
    print("=" * 60)
    
    all_tests_passed = True
    connections = {}
    
    # Test connections to all databases
    for db_name, config in DATABASES.items():
        conn = test_connection(db_name, config)
        if conn:
            connections[db_name] = conn
        else:
            all_tests_passed = False
    
    if not connections:
        print_status("❌ No database connections available. Exiting.", "ERROR")
        sys.exit(1)
    
    # Test each database functionality
    if 'raw' in connections:
        if not test_raw_database(connections['raw']):
            all_tests_passed = False
    
    if 'analytics' in connections:
        if not test_analytics_database(connections['analytics']):
            all_tests_passed = False
    
    if 'logging' in connections:
        if not test_logging_database(connections['logging']):
            all_tests_passed = False
    
    # Test connection pooling
    if not test_connection_pooling():
        all_tests_passed = False
    
    # Close all connections
    for conn in connections.values():
        conn.close()
    
    print("=" * 60)
    if all_tests_passed:
        print_status("🎉 All database tests passed successfully!", "SUCCESS")
        sys.exit(0)
    else:
        print_status("❌ Some database tests failed. Please check the logs above.", "ERROR")
        sys.exit(1)

if __name__ == "__main__":
    main()