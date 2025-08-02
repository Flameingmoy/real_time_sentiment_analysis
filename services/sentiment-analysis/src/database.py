"""Database operations for analytics data"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

import asyncpg
from asyncpg import Pool

@dataclass
class SentimentRecord:
    """Sentiment analysis record"""
    id: str
    source: str
    source_id: str
    content: Dict[str, Any]
    sentiment: str
    score: float
    confidence: float
    entities: List[Dict[str, Any]]
    financial_sentiment: Optional[Dict[str, Any]] = None
    vector_hash: Optional[str] = None
    processed_at: datetime = None
    processing_time_ms: int = 0

@dataclass
class AggregatedSentiment:
    """Aggregated sentiment data"""
    time_bucket: datetime
    source: str
    sentiment: str
    count: int
    avg_score: float
    avg_confidence: float
    entities: List[Dict[str, Any]]

class AnalyticsDatabase:
    """Database operations for analytics"""
    
    def __init__(self, config):
        self.config = config
        self.pool: Optional[Pool] = None
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self):
        """Initialize database connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.user,
                password=self.config.password,
                min_size=self.config.pool_size,
                max_size=self.config.max_overflow,
                command_timeout=self.config.pool_timeout
            )
            
            await self.create_tables()
            self.logger.info("Analytics database initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def create_tables(self):
        """Create required tables"""
        async with self.pool.acquire() as conn:
            # Create sentiment analysis table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS sentiment_analysis (
                    id UUID PRIMARY KEY,
                    source VARCHAR(50) NOT NULL,
                    source_id VARCHAR(255),
                    content JSONB NOT NULL,
                    sentiment VARCHAR(20) NOT NULL,
                    score DECIMAL(3,2) NOT NULL,
                    confidence DECIMAL(3,2) NOT NULL,
                    entities JSONB,
                    financial_sentiment JSONB,
                    vector_hash VARCHAR(64),
                    processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    processing_time_ms INTEGER DEFAULT 0,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            
            # Create aggregated sentiment table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS aggregated_sentiment (
                    id SERIAL PRIMARY KEY,
                    time_bucket TIMESTAMP WITH TIME ZONE NOT NULL,
                    source VARCHAR(50) NOT NULL,
                    sentiment VARCHAR(20) NOT NULL,
                    count INTEGER NOT NULL,
                    avg_score DECIMAL(3,2) NOT NULL,
                    avg_confidence DECIMAL(3,2) NOT NULL,
                    entities JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            
            # Create indexes
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sentiment_analysis_source 
                ON sentiment_analysis(source)
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sentiment_analysis_processed_at 
                ON sentiment_analysis(processed_at)
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sentiment_analysis_sentiment 
                ON sentiment_analysis(sentiment)
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sentiment_analysis_vector_hash 
                ON sentiment_analysis(vector_hash)
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_aggregated_sentiment_time_bucket 
                ON aggregated_sentiment(time_bucket)
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_aggregated_sentiment_source 
                ON aggregated_sentiment(source)
            """)
            
            self.logger.info("Database tables and indexes created successfully")
    
    async def store_sentiment(self, record: SentimentRecord) -> bool:
        """Store sentiment analysis result"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO sentiment_analysis (
                        id, source, source_id, content, sentiment, 
                        score, confidence, entities, financial_sentiment,
                        vector_hash, processed_at, processing_time_ms
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                """,
                    record.id,
                    record.source,
                    record.source_id,
                    json.dumps(record.content),
                    record.sentiment,
                    record.score,
                    record.confidence,
                    json.dumps(record.entities),
                    json.dumps(record.financial_sentiment) if record.financial_sentiment else None,
                    record.vector_hash,
                    record.processed_at,
                    record.processing_time_ms
                )
            
            self.logger.debug(f"Stored sentiment analysis for {record.id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store sentiment: {e}")
            return False

    async def store_sentiments_batch(self, records: List[SentimentRecord]) -> bool:
        """Store a batch of sentiment analysis results."""
        if not records:
            return True
            
        try:
            async with self.pool.acquire() as conn:
                # Prepare data for executemany
                data_to_insert = []
                for record in records:
                    data_to_insert.append((
                        record.id,
                        record.source,
                        record.source_id,
                        json.dumps(record.content),
                        record.sentiment,
                        record.score,
                        record.confidence,
                        json.dumps(record.entities),
                        json.dumps(record.financial_sentiment) if record.financial_sentiment else None,
                        record.vector_hash,
                        record.processed_at,
                        record.processing_time_ms
                    ))

                await conn.executemany("""
                    INSERT INTO sentiment_analysis (
                        id, source, source_id, content, sentiment, score, 
                        confidence, entities, financial_sentiment, vector_hash, 
                        processed_at, processing_time_ms
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                """, data_to_insert)

            self.logger.info(f"Stored a batch of {len(records)} sentiment records.")
            return True

        except Exception as e:
            self.logger.error(f"Failed to store sentiment batch: {e}")
            return False
    
    async def get_sentiment_by_hash(self, vector_hash: str) -> Optional[SentimentRecord]:
        """Get sentiment by vector hash (deduplication)"""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT * FROM sentiment_analysis 
                    WHERE vector_hash = $1 
                    ORDER BY processed_at DESC 
                    LIMIT 1
                """, vector_hash)
                
                if row:
                    return SentimentRecord(
                        id=row['id'],
                        source=row['source'],
                        source_id=row['source_id'],
                        content=row['content'],
                        sentiment=row['sentiment'],
                        score=float(row['score']),
                        confidence=float(row['confidence']),
                        entities=row['entities'],
                        financial_sentiment=row['financial_sentiment'],
                        vector_hash=row['vector_hash'],
                        processed_at=row['processed_at'],
                        processing_time_ms=row['processing_time_ms']
                    )
                
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to get sentiment by hash: {e}")
            return None
    
    async def get_sentiment_stats(self, source: str = None, 
                                time_from: datetime = None, 
                                time_to: datetime = None) -> Dict[str, Any]:
        """Get sentiment statistics"""
        try:
            async with self.pool.acquire() as conn:
                query = """
                    SELECT 
                        sentiment,
                        COUNT(*) as count,
                        AVG(score) as avg_score,
                        AVG(confidence) as avg_confidence
                    FROM sentiment_analysis
                    WHERE 1=1
                """
                params = []
                
                if source:
                    query += " AND source = $1"
                    params.append(source)
                
                if time_from:
                    param_num = len(params) + 1
                    query += f" AND processed_at >= ${param_num}"
                    params.append(time_from)
                
                if time_to:
                    param_num = len(params) + 1
                    query += f" AND processed_at <= ${param_num}"
                    params.append(time_to)
                
                query += " GROUP BY sentiment"
                
                rows = await conn.fetch(query, *params)
                
                stats = {
                    'total': 0,
                    'sentiments': {},
                    'avg_score': 0.0,
                    'avg_confidence': 0.0
                }
                
                total_count = 0
                total_score = 0.0
                total_confidence = 0.0
                
                for row in rows:
                    stats['sentiments'][row['sentiment']] = {
                        'count': row['count'],
                        'avg_score': float(row['avg_score']),
                        'avg_confidence': float(row['avg_confidence'])
                    }
                    total_count += row['count']
                    total_score += float(row['avg_score']) * row['count']
                    total_confidence += float(row['avg_confidence']) * row['count']
                
                stats['total'] = total_count
                if total_count > 0:
                    stats['avg_score'] = total_score / total_count
                    stats['avg_confidence'] = total_confidence / total_count
                
                return stats
                
        except Exception as e:
            self.logger.error(f"Failed to get sentiment stats: {e}")
            return {'total': 0, 'sentiments': {}, 'avg_score': 0.0, 'avg_confidence': 0.0}
    
    async def store_aggregated_sentiment(self, aggregated: AggregatedSentiment) -> bool:
        """Store aggregated sentiment data"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO aggregated_sentiment (
                        time_bucket, source, sentiment, count, 
                        avg_score, avg_confidence, entities
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                    aggregated.time_bucket,
                    aggregated.source,
                    aggregated.sentiment,
                    aggregated.count,
                    aggregated.avg_score,
                    aggregated.avg_confidence,
                    json.dumps(aggregated.entities)
                )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store aggregated sentiment: {e}")
            return False
    
    async def health_check(self) -> bool:
        """Check database health"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("SELECT 1")
            return True
        except Exception as e:
            self.logger.error(f"Database health check failed: {e}")
            return False
    
    async def close(self):
        """Close database connection"""
        if self.pool:
            await self.pool.close()
            self.logger.info("Database connection closed")
