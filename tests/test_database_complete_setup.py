#!/usr/bin/env python3
"""
Comprehensive Database Setup Test
Tests all three PostgreSQL databases with connection pooling and schema validation
"""

from psycopg2 import pool
from psycopg2.extras import Json
import time
from datetime import datetime, timezone
import sys

# Database configurations
DB_CONFIGS = {
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

class DatabaseTester:
    def __init__(self):
        self.connection_pools = {}
        self.test_results = {}
    
    def create_connection_pools(self):
        """Create connection pools for all databases"""
        print("🔗 Creating connection pools...")
        
        for db_name, config in DB_CONFIGS.items():
            try:
                # Create connection pool with proper configuration
                pool_config = {
                    **config,
                    'minconn': 2,
                    'maxconn': 10
                }
                
                self.connection_pools[db_name] = pool.ThreadedConnectionPool(**pool_config)
                print(f"✅ Connection pool created for {db_name} database")
                
            except Exception as e:
                print(f"❌ Failed to create connection pool for {db_name}: {e}")
                return False
        
        return True
    
    def test_database_connection(self, db_name):
        """Test basic database connection and health"""
        print(f"\n🔍 Testing {db_name} database connection...")
        
        try:
            pool = self.connection_pools[db_name]
            conn = pool.getconn()
            
            with conn.cursor() as cursor:
                # Test basic connection
                cursor.execute("SELECT version();")
                version = cursor.fetchone()[0]
                print(f"✅ Connected to {db_name}: {version[:50]}...")
                
                # Test database-specific functionality
                if db_name == 'raw':
                    self.test_raw_database_schema(cursor)
                elif db_name == 'analytics':
                    self.test_analytics_database_schema(cursor)
                elif db_name == 'logging':
                    self.test_logging_database_schema(cursor)
            
            pool.putconn(conn)
            self.test_results[db_name] = True
            return True
            
        except Exception as e:
            print(f"❌ {db_name} database test failed: {e}")
            self.test_results[db_name] = False
            return False
    
    def test_raw_database_schema(self, cursor):
        """Test raw database schema and functionality"""
        print("  📋 Testing raw database schema...")
        
        # Check if raw_data table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'raw_data'
            );
        """)
        
        if not cursor.fetchone()[0]:
            raise Exception("raw_data table does not exist")
        
        # Check partitioning
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_name LIKE 'raw_data_%' 
            AND table_schema = 'public';
        """)
        
        partition_count = cursor.fetchone()[0]
        print(f"  ✅ Found {partition_count} partitions for raw_data table")
        
        # Test data insertion
        test_data = {
            'source': 'test_source',
            'source_id': 'test_123',
            'content': Json({'message': 'Test message', 'value': 42}),
            'timestamp': datetime.now(timezone.utc),
            'content_hash': 'test_hash_' + str(int(time.time()))
        }
        
        cursor.execute("""
            INSERT INTO raw_data (source, source_id, content, timestamp, content_hash)
            VALUES (%(source)s, %(source_id)s, %(content)s, %(timestamp)s, %(content_hash)s)
            RETURNING id;
        """, test_data)
        
        inserted_id = cursor.fetchone()[0]
        print(f"  ✅ Successfully inserted test record with ID: {inserted_id}")
        
        # Test indexes
        cursor.execute("""
            SELECT indexname FROM pg_indexes 
            WHERE tablename = 'raw_data' 
            AND schemaname = 'public';
        """)
        
        indexes = [row[0] for row in cursor.fetchall()]
        expected_indexes = ['idx_raw_data_timestamp', 'idx_raw_data_source', 'idx_raw_data_content_hash']
        
        for expected_idx in expected_indexes:
            if any(expected_idx in idx for idx in indexes):
                print(f"  ✅ Index {expected_idx} exists")
            else:
                print(f"  ⚠️  Index {expected_idx} not found")
    
    def test_analytics_database_schema(self, cursor):
        """Test analytics database schema and functionality"""
        print("  📊 Testing analytics database schema...")
        
        # Check if sentiment_results table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'sentiment_results'
            );
        """)
        
        if not cursor.fetchone()[0]:
            raise Exception("sentiment_results table does not exist")
        
        # Test data insertion
        test_data = {
            'source_id': 'test_source_123',
            'content_hash': 'test_hash_' + str(int(time.time())),
            'timestamp': datetime.now(timezone.utc),
            'source_type': 'news',
            'content': 'This is a positive test message about the market.',
            'sentiment_score': 0.75,
            'sentiment_label': 'positive',
            'confidence_score': 0.85,
            'entities': Json({'companies': ['AAPL', 'GOOGL'], 'sentiment_keywords': ['positive', 'growth']}),
            'metadata': Json({'model_version': '1.0', 'processing_time': 2.5})
        }
        
        cursor.execute("""
            INSERT INTO sentiment_results 
            (source_id, content_hash, timestamp, source_type, content, sentiment_score, 
             sentiment_label, confidence_score, entities, metadata)
            VALUES (%(source_id)s, %(content_hash)s, %(timestamp)s, %(source_type)s, 
                    %(content)s, %(sentiment_score)s, %(sentiment_label)s, 
                    %(confidence_score)s, %(entities)s, %(metadata)s)
            RETURNING id;
        """, test_data)
        
        inserted_id = cursor.fetchone()[0]
        print(f"  ✅ Successfully inserted sentiment result with ID: {inserted_id}")
        
        # Check materialized views
        cursor.execute("""
            SELECT matviewname FROM pg_matviews 
            WHERE schemaname = 'public';
        """)
        
        views = [row[0] for row in cursor.fetchall()]
        expected_views = ['hourly_sentiment_summary', 'daily_sentiment_summary', 'source_volume_metrics']
        
        for expected_view in expected_views:
            if expected_view in views:
                print(f"  ✅ Materialized view {expected_view} exists")
            else:
                print(f"  ⚠️  Materialized view {expected_view} not found")
        
        # Test entity_summary table
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'entity_summary'
            );
        """)
        
        if cursor.fetchone()[0]:
            print("  ✅ entity_summary table exists")
        else:
            print("  ⚠️  entity_summary table not found")
    
    def test_logging_database_schema(self, cursor):
        """Test logging database schema and functionality"""
        print("  📝 Testing logging database schema...")
        
        # Check if system_logs table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'system_logs'
            );
        """)
        
        if not cursor.fetchone()[0]:
            raise Exception("system_logs table does not exist")
        
        # Check partitioning
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_name LIKE 'system_logs_%' 
            AND table_schema = 'public';
        """)
        
        partition_count = cursor.fetchone()[0]
        print(f"  ✅ Found {partition_count} partitions for system_logs table")
        
        # Test log insertion
        test_log = {
            'level': 'INFO',
            'component': 'database_test',
            'message': 'Test log message for database validation',
            'metadata': Json({'test_id': 'db_test_001', 'timestamp': time.time()})
        }
        
        cursor.execute("""
            INSERT INTO system_logs (level, component, message, metadata)
            VALUES (%(level)s, %(component)s, %(message)s, %(metadata)s)
            RETURNING id;
        """, test_log)
        
        inserted_id = cursor.fetchone()[0]
        print(f"  ✅ Successfully inserted log with ID: {inserted_id}")
        
        # Check error_summary table
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'error_summary'
            );
        """)
        
        if cursor.fetchone()[0]:
            print("  ✅ error_summary table exists")
        else:
            print("  ⚠️  error_summary table not found")
        
        # Check performance_metrics table
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'performance_metrics'
            );
        """)
        
        if cursor.fetchone()[0]:
            print("  ✅ performance_metrics table exists")
        else:
            print("  ⚠️  performance_metrics table not found")
    
    def test_connection_pooling(self):
        """Test connection pooling functionality"""
        print("\n🏊 Testing connection pooling...")
        
        for db_name, pool in self.connection_pools.items():
            try:
                # Get multiple connections simultaneously
                connections = []
                for i in range(5):
                    conn = pool.getconn()
                    connections.append(conn)
                
                print(f"  ✅ Successfully obtained 5 connections from {db_name} pool")
                
                # Return connections to pool
                for conn in connections:
                    pool.putconn(conn)
                
                print(f"  ✅ Successfully returned connections to {db_name} pool")
                
            except Exception as e:
                print(f"  ❌ Connection pooling test failed for {db_name}: {e}")
    
    def test_performance_queries(self):
        """Test performance of key database queries"""
        print("\n⚡ Testing query performance...")
        
        # Test analytics database query performance
        try:
            pool = self.connection_pools['analytics']
            conn = pool.getconn()
            
            with conn.cursor() as cursor:
                # Test a complex query that would be used in dashboards
                start_time = time.time()
                cursor.execute("""
                    SELECT 
                        source_type,
                        sentiment_label,
                        COUNT(*) as count,
                        AVG(sentiment_score) as avg_score,
                        AVG(confidence_score) as avg_confidence
                    FROM sentiment_results 
                    WHERE timestamp > NOW() - INTERVAL '1 hour'
                    GROUP BY source_type, sentiment_label
                    ORDER BY count DESC;
                """)
                
                results = cursor.fetchall()
                query_time = time.time() - start_time
                
                print(f"  ✅ Analytics query completed in {query_time:.3f}s (found {len(results)} result groups)")
                
                if query_time > 0.5:  # 500ms threshold from requirements
                    print(f"  ⚠️  Query time ({query_time:.3f}s) exceeds 500ms threshold")
            
            pool.putconn(conn)
            
        except Exception as e:
            print(f"  ❌ Performance query test failed: {e}")
    
    def cleanup_test_data(self):
        """Clean up test data inserted during testing"""
        print("\n🧹 Cleaning up test data...")
        
        try:
            # Clean up raw database
            pool = self.connection_pools['raw']
            conn = pool.getconn()
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM raw_data WHERE source = 'test_source';")
                conn.commit()
            pool.putconn(conn)
            
            # Clean up analytics database
            pool = self.connection_pools['analytics']
            conn = pool.getconn()
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM sentiment_results WHERE source_id LIKE 'test_source_%';")
                conn.commit()
            pool.putconn(conn)
            
            # Clean up logging database
            pool = self.connection_pools['logging']
            conn = pool.getconn()
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM system_logs WHERE component = 'database_test';")
                conn.commit()
            pool.putconn(conn)
            
            print("✅ Test data cleaned up successfully")
            
        except Exception as e:
            print(f"⚠️  Failed to clean up test data: {e}")
    
    def close_connections(self):
        """Close all connection pools"""
        print("\n🔒 Closing connection pools...")
        
        for db_name, pool in self.connection_pools.items():
            try:
                pool.closeall()
                print(f"✅ Closed connection pool for {db_name}")
            except Exception as e:
                print(f"⚠️  Failed to close pool for {db_name}: {e}")
    
    def run_all_tests(self):
        """Run all database tests"""
        print("🚀 Starting comprehensive database setup test...\n")
        
        # Create connection pools
        if not self.create_connection_pools():
            print("❌ Failed to create connection pools. Exiting.")
            return False
        
        # Test each database
        all_passed = True
        for db_name in DB_CONFIGS.keys():
            if not self.test_database_connection(db_name):
                all_passed = False
        
        # Test connection pooling
        self.test_connection_pooling()
        
        # Test performance
        self.test_performance_queries()
        
        # Clean up
        self.cleanup_test_data()
        self.close_connections()
        
        # Print summary
        print("\n" + "="*50)
        print("📊 DATABASE SETUP TEST SUMMARY")
        print("="*50)
        
        for db_name, result in self.test_results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{db_name.upper()} Database: {status}")
        
        overall_status = "✅ ALL TESTS PASSED" if all_passed else "❌ SOME TESTS FAILED"
        print(f"\nOverall Status: {overall_status}")
        
        return all_passed

def main():
    """Main function to run database tests"""
    tester = DatabaseTester()
    
    try:
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        tester.close_connections()
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ Unexpected error during testing: {e}")
        tester.close_connections()
        sys.exit(1)

if __name__ == "__main__":
    main()