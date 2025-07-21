#!/usr/bin/env python3
"""
Test script for Redis vector storage functionality
Tests vector storage, similarity search, and RedisSearch module
"""

import redis
import numpy as np
import json
import time
import uuid
from datetime import datetime
import hashlib

class RedisVectorTest:
    def __init__(self, host='localhost', port=6380, db=0):
        self.host = host
        self.port = port
        self.db = db
        self.redis_client = None
        self.index_name = "test_embedding_idx"
        self.key_prefix = "test:embedding:"
        
    def connect(self):
        """Connect to Redis and verify RedisSearch module"""
        try:
            self.redis_client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                decode_responses=False  # Keep binary for vector operations
            )
            
            # Test connection
            self.redis_client.ping()
            print("✓ Connected to Redis successfully")
            
            # Check if RedisSearch module is loaded
            modules = self.redis_client.module_list()
            search_module = any(module[b'name'] == b'search' for module in modules)
            
            if search_module:
                print("✓ RedisSearch module is loaded")
                return True
            else:
                print("✗ RedisSearch module is not loaded")
                return False
                
        except Exception as e:
            print(f"✗ Failed to connect to Redis: {e}")
            return False
    
    def cleanup_test_data(self):
        """Clean up any existing test data"""
        try:
            # Delete test index if exists
            try:
                self.redis_client.execute_command("FT.DROPINDEX", self.index_name, "DD")
                print("✓ Cleaned up existing test index")
            except:
                pass  # Index might not exist
            
            # Delete test keys
            keys = self.redis_client.keys(f"{self.key_prefix}*")
            if keys:
                self.redis_client.delete(*keys)
                print(f"✓ Cleaned up {len(keys)} test keys")
            
        except Exception as e:
            print(f"Warning: Cleanup failed: {e}")
    
    def create_vector_index(self):
        """Create vector index for similarity search"""
        try:
            # Create index with vector field
            index_definition = [
                "ON", "HASH",
                "PREFIX", "1", self.key_prefix,
                "SCHEMA",
                "vector", "VECTOR", "FLAT", "6",
                "TYPE", "FLOAT32",
                "DIM", "384",  # Using smaller dimension for testing
                "DISTANCE_METRIC", "COSINE",
                "content", "TEXT",
                "timestamp", "NUMERIC", "SORTABLE"
            ]
            
            self.redis_client.execute_command("FT.CREATE", self.index_name, *index_definition)
            print("✓ Vector index created successfully")
            return True
            
        except Exception as e:
            if "Index already exists" in str(e):
                print("✓ Vector index already exists")
                return True
            else:
                print(f"✗ Failed to create vector index: {e}")
                return False
    
    def generate_test_vector(self, text, dimension=384):
        """Generate a test vector from text (simple hash-based approach)"""
        # Create a deterministic vector from text hash
        hash_obj = hashlib.md5(text.encode())
        hash_bytes = hash_obj.digest()
        
        # Convert to numpy array and normalize
        vector = np.frombuffer(hash_bytes * (dimension // 16 + 1), dtype=np.float32)[:dimension]
        
        # Avoid division by zero
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        else:
            vector = np.random.random(dimension).astype(np.float32)
            vector = vector / np.linalg.norm(vector)
        
        return vector.astype(np.float32)
    
    def store_vector(self, content, metadata=None):
        """Store a vector with content and metadata"""
        try:
            # Generate vector from content
            vector = self.generate_test_vector(content)
            
            # Create unique key
            content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
            key = f"{self.key_prefix}{content_hash}"
            
            # Prepare data
            data = {
                "vector": vector.tobytes(),
                "content": content,
                "timestamp": int(time.time()),
                "content_hash": content_hash
            }
            
            if metadata:
                data.update(metadata)
            
            # Store in Redis
            self.redis_client.hset(key, mapping=data)
            
            print(f"✓ Stored vector for content: '{content[:50]}...'")
            print(f"  - Key: {key}")
            print(f"  - Vector dimension: {len(vector)}")
            
            return key, vector
            
        except Exception as e:
            print(f"✗ Failed to store vector: {e}")
            return None, None
    
    def search_similar_vectors(self, query_vector, k=5, threshold=0.8):
        """Search for similar vectors"""
        try:
            # Convert vector to bytes
            query_bytes = query_vector.tobytes()
            
            # Perform vector search using correct syntax
            result = self.redis_client.execute_command(
                "FT.SEARCH", self.index_name,
                f"*=>[KNN {k} @vector $query_vec AS score]",
                "PARAMS", "2", "query_vec", query_bytes,
                "RETURN", "3", "content", "score", "content_hash",
                "SORTBY", "score", "ASC",
                "LIMIT", "0", str(k)
            )
            
            # Parse results
            num_results = result[0]
            results = []
            
            for i in range(1, len(result), 2):
                key = result[i].decode('utf-8')
                fields = result[i + 1]
                
                # Parse fields
                field_dict = {}
                for j in range(0, len(fields), 2):
                    field_name = fields[j].decode('utf-8')
                    field_value = fields[j + 1].decode('utf-8')
                    field_dict[field_name] = field_value
                
                results.append({
                    'key': key,
                    'content': field_dict.get('content', ''),
                    'score': float(field_dict.get('score', 1.0)),
                    'content_hash': field_dict.get('content_hash', '')
                })
            
            print(f"✓ Found {num_results} similar vectors")
            for i, result in enumerate(results):
                similarity = 1 - result['score']  # Convert distance to similarity
                print(f"  {i+1}. Similarity: {similarity:.3f} - Content: '{result['content'][:50]}...'")
            
            return results
            
        except Exception as e:
            print(f"✗ Failed to search vectors: {e}")
            print(f"Debug: Query vector shape: {query_vector.shape}, dtype: {query_vector.dtype}")
            return []
    
    def test_vector_operations(self):
        """Test complete vector storage and search workflow"""
        print("\n--- Testing Vector Storage Operations ---")
        
        # Test data
        test_contents = [
            "Apple stock price rises due to strong iPhone sales",
            "Apple announces new iPhone with improved features",
            "Tesla stock drops after production delays",
            "Electric vehicle market shows strong growth",
            "Federal Reserve raises interest rates",
            "Inflation concerns impact stock market"
        ]
        
        stored_vectors = []
        
        # Store test vectors
        print("\nStoring test vectors...")
        for content in test_contents:
            key, vector = self.store_vector(content, {"source": "test"})
            if key and vector is not None:
                stored_vectors.append((key, vector, content))
        
        if not stored_vectors:
            print("✗ No vectors were stored successfully")
            return False
        
        # Wait for indexing
        time.sleep(2)
        
        # Test similarity search
        print("\nTesting similarity search...")
        query_content = "Apple iPhone stock performance"
        query_vector = self.generate_test_vector(query_content)
        
        print(f"Query: '{query_content}'")
        similar_results = self.search_similar_vectors(query_vector, k=3)
        
        if not similar_results:
            print("✗ No similar vectors found")
            return False
        
        # Test duplicate detection (95% threshold)
        print("\nTesting duplicate detection...")
        duplicate_content = test_contents[0]  # Use exact duplicate
        duplicate_vector = self.generate_test_vector(duplicate_content)
        duplicate_results = self.search_similar_vectors(duplicate_vector, k=1)
        
        if duplicate_results:
            similarity = 1 - duplicate_results[0]['score']
            if similarity >= 0.95:
                print(f"✓ Duplicate detected with {similarity:.3f} similarity (>= 0.95 threshold)")
            else:
                print(f"✗ Duplicate detection failed: {similarity:.3f} similarity (< 0.95 threshold)")
                return False
        else:
            print("✗ No results for duplicate detection test")
            return False
        
        return True
    
    def test_performance(self):
        """Test vector search performance"""
        print("\n--- Testing Vector Search Performance ---")
        
        # Store some vectors for performance testing
        test_content = "Performance test vector content"
        key, vector = self.store_vector(test_content)
        
        if not key or vector is None:
            print("✗ Failed to store vector for performance test")
            return False
        
        # Wait for indexing
        time.sleep(1)
        
        # Measure search performance
        num_searches = 10
        total_time = 0
        
        for i in range(num_searches):
            start_time = time.time()
            results = self.search_similar_vectors(vector, k=1)
            end_time = time.time()
            
            search_time = (end_time - start_time) * 1000  # Convert to milliseconds
            total_time += search_time
            
            if not results:
                print(f"✗ Search {i+1} failed")
                return False
        
        avg_time = total_time / num_searches
        print(f"✓ Average search time: {avg_time:.2f}ms ({num_searches} searches)")
        
        # Check if meets performance requirement (<100ms)
        if avg_time < 100:
            print("✓ Performance requirement met (<100ms)")
            return True
        else:
            print(f"✗ Performance requirement not met: {avg_time:.2f}ms >= 100ms")
            return False
    
    def run_all_tests(self):
        """Run all Redis vector tests"""
        print("Starting Redis vector storage tests...")
        print(f"Redis server: {self.host}:{self.port}")
        
        # Connect to Redis
        if not self.connect():
            return False
        
        # Cleanup previous test data
        self.cleanup_test_data()
        
        # Create vector index
        if not self.create_vector_index():
            return False
        
        # Test vector operations
        if not self.test_vector_operations():
            return False
        
        # Test performance
        if not self.test_performance():
            return False
        
        # Cleanup after tests
        self.cleanup_test_data()
        
        print("\n" + "="*50)
        print("✓ ALL REDIS VECTOR TESTS PASSED")
        print("="*50)
        
        return True

if __name__ == "__main__":
    # Run Redis vector tests
    redis_test = RedisVectorTest()
    success = redis_test.run_all_tests()
    
    if not success:
        print("\n" + "="*50)
        print("✗ SOME REDIS VECTOR TESTS FAILED")
        print("="*50)
        exit(1)
    
    exit(0)