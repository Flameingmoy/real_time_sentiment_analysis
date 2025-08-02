"""Redis vector store for embeddings and deduplication"""

import asyncio
import hashlib
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

import redis.asyncio as redis
import numpy as np
from redis.commands.search.field import VectorField, TextField, NumericField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.commands.search.query import Query

class VectorStore:
    """Redis-based vector store for embeddings and deduplication"""
    
    def __init__(self, config):
        self.config = config
        self.redis_client = None
        self.logger = logging.getLogger(__name__)
    async def initialize(self):
        """Initialize Redis connection and create search index if it doesn't exist."""
        try:
            self.redis_client = redis.Redis(
                host=self.config.host,
                port=self.config.port,
                password=self.config.password,
                db=self.config.db,
                decode_responses=False,  # Set to False for vector operations
                socket_timeout=self.config.socket_timeout,
                socket_connect_timeout=self.config.socket_connect_timeout
            )
            await self.redis_client.ping()
            self.logger.info("Redis connection successful.")

            # Create RedisSearch index
            await self._create_search_index()

        except Exception as e:
            self.logger.error(f"Failed to initialize Redis or create index: {e}")
            raise
    
    def generate_content_hash(self, content: Dict[str, Any]) -> str:
        """Generate hash for content deduplication"""
        # Normalize content for consistent hashing
        normalized = json.dumps(content, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(normalized.encode()).hexdigest()
    
    async def is_duplicate(self, content_hash: str, ttl: int = 3600) -> bool:
        """Check if content is duplicate"""
        try:
            key = f"content_hash:{content_hash}"
            exists = await self.redis_client.exists(key)
            
            if exists:
                # Update TTL for existing entry
                await self.redis_client.expire(key, ttl)
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to check duplicate: {e}")
            return False
    
    async def mark_processed(self, content_hash: str, metadata: Dict[str, Any], ttl: int = 3600):
        """Mark content as processed"""
        try:
            key = f"content_hash:{content_hash}"
            value = json.dumps({
                'processed_at': datetime.utcnow().isoformat(),
                'metadata': metadata
            })
            
            await self.redis_client.setex(key, ttl, value)
            
        except Exception as e:
            self.logger.error(f"Failed to mark processed: {e}")
    async def store_embedding(self, content_id: str, embedding: List[float], metadata: Dict[str, Any]):
        """Store embedding vector in RedisSearch index."""
        try:
            key = f"{self.config.index_name}:{content_id}"
            embedding_bytes = np.array(embedding, dtype=np.float32).tobytes()

            mapping = {
                'content_id': content_id,
                'embedding': embedding_bytes,
                'created_at': int(datetime.utcnow().timestamp()),
                'metadata': json.dumps(metadata)
            }

            await self.redis_client.hset(key, mapping=mapping)
            self.logger.info(f"Stored embedding for content_id: {content_id}")

        except Exception as e:
            self.logger.error(f"Failed to store embedding: {e}")
    async def get_embedding(self, content_id: str) -> Optional[List[float]]:
        """Retrieve embedding vector from RedisHash."""
        try:
            key = f"{self.config.index_name}:{content_id}"
            embedding_bytes = await self.redis_client.hget(key, 'embedding')
            
            if embedding_bytes:
                return np.frombuffer(embedding_bytes, dtype=np.float32).tolist()
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get embedding: {e}")
            return None
    
    async def find_similar(self, embedding: List[float], top_k: int = 10) -> List[Dict[str, Any]]:
        """Find similar embeddings using RedisSearch vector similarity."""
        try:
            query_vector = np.array(embedding, dtype=np.float32).tobytes()
            
            q = (
                Query("*=>[KNN $k @embedding $query_vector AS vector_score]")
                .sort_by("vector_score")
                .return_fields("content_id", "vector_score", "metadata")
                .dialect(2)
            )

            params = {"k": top_k, "query_vector": query_vector}
            results = await self.redis_client.ft(self.config.index_name).search(q, query_params=params)

            similar_items = []
            for doc in results.docs:
                similar_items.append({
                    'content_id': doc.content_id,
                    'similarity_score': doc.vector_score,
                    'metadata': json.loads(doc.metadata)
                })
            
            return similar_items

        except Exception as e:
            self.logger.error(f"Failed to find similar embeddings: {e}")
            return []
    
    async def store_sentiment_cache(self, content_hash: str, sentiment: Dict[str, Any], ttl: int = 3600):
        """Cache sentiment analysis results"""
        try:
            key = f"sentiment:{content_hash}"
            data = {
                'sentiment': sentiment,
                'cached_at': datetime.utcnow().isoformat()
            }
            
            await self.redis_client.setex(key, ttl, json.dumps(data))
            
        except Exception as e:
            self.logger.error(f"Failed to cache sentiment: {e}")
    
    async def get_sentiment_cache(self, content_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached sentiment analysis"""
        try:
            key = f"sentiment:{content_hash}"
            data = await self.redis_client.get(key)
            
            if data:
                parsed = json.loads(data)
                return parsed.get('sentiment')
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get sentiment cache: {e}")
            return None
    
    async def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        try:
            # Count processed items
            hash_keys = await self.redis_client.keys("content_hash:*")
            embedding_keys = await self.redis_client.keys("embedding:*")
            sentiment_keys = await self.redis_client.keys("sentiment:*")
            
            # Get TTLs for all keys
            total_ttl = 0
            keys_with_ttl = await self.redis_client.keys("*")
            
            for key in keys_with_ttl:
                ttl = await self.redis_client.ttl(key)
                if ttl > 0:
                    total_ttl += ttl
            
            return {
                'processed_items': len(hash_keys),
                'stored_embeddings': len(embedding_keys),
                'cached_sentiments': len(sentiment_keys),
                'total_ttl': total_ttl
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get processing stats: {e}")
            return {}
    
    async def cleanup_expired(self):
        """Clean up expired keys"""
        try:
            keys = await self.redis_client.keys("*")
            expired_count = 0
            
            for key in keys:
                ttl = await self.redis_client.ttl(key)
                if ttl == -2:  # Key doesn't exist or expired
                    await self.redis_client.delete(key)
                    expired_count += 1
            
            self.logger.info(f"Cleaned up {expired_count} expired keys")
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup expired keys: {e}")
    
    async def health_check(self) -> bool:
        """Check Redis health"""
        try:
            await self.redis_client.ping()
            return True
        except Exception as e:
            self.logger.error(f"Redis health check failed: {e}")
            return False
    async def _create_search_index(self):
        """Create the search index if it does not exist."""
        try:
            schema = (
                TextField("content_id"),
                VectorField("embedding", "FLAT", {
                    "TYPE": "FLOAT32",
                    "DIM": self.config.embedding_dim,
                    "DISTANCE_METRIC": "COSINE",
                }),
                NumericField("created_at"),
                TextField("metadata")
            )
            
            # Index Definition
            definition = IndexDefinition(prefix=[f"{self.config.index_name}:"], index_type=IndexType.HASH)

            # Check if index exists
            try:
                await self.redis_client.ft(self.config.index_name).info()
                self.logger.info(f"Index '{self.config.index_name}' already exists.")
            except redis.exceptions.ResponseError:
                # Index does not exist, create it
                await self.redis_client.ft(self.config.index_name).create_index(fields=schema, definition=definition)
                self.logger.info(f"Created index '{self.config.index_name}'.")

        except Exception as e:
            self.logger.error(f"Failed to create search index: {e}")
            raise

    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            self.logger.info("Redis connection closed")
