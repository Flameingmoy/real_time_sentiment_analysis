"""Kafka consumer service for sentiment analysis"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

from kafka import KafkaConsumer
from kafka.errors import KafkaError

from src.database import SentimentRecord
from src.sentiment import SentimentAnalyzer
from src.vector_store import VectorStore
from src.metrics import (
    MESSAGES_PROCESSED_TOTAL,
    ERRORS_TOTAL,
    MESSAGE_PROCESSING_LATENCY,
    BATCH_SIZE,
    DATABASE_OPERATIONS_TOTAL,
    DATABASE_OPERATION_LATENCY
)

class KafkaConsumerService:
    """Kafka consumer for sentiment analysis"""
    
    def __init__(self, kafka_config, analyzer, database, vector_store):
        self.config = kafka_config
        self.analyzer = analyzer
        self.database = database
        self.vector_store = vector_store
        self.consumer = None
        self.logger = logging.getLogger(__name__)
        self.running = False
        self.processed_count = 0
        self.error_count = 0
        self.batch = []
        self.last_flush_time = time.time()
        
    async def initialize_consumer(self):
        """Initialize Kafka consumer"""
        try:
            self.consumer = KafkaConsumer(
                self.config.topics['sentiment_analysis'],
                bootstrap_servers=self.config.bootstrap_servers,
                group_id=self.config.group_id,
                auto_offset_reset=self.config.auto_offset_reset,
                enable_auto_commit=self.config.enable_auto_commit,
                max_poll_records=self.config.max_poll_records,
                session_timeout_ms=self.config.session_timeout_ms,
                heartbeat_interval_ms=self.config.heartbeat_interval_ms,
                value_deserializer=lambda m: json.loads(m.decode('utf-8'))
            )
            
            self.logger.info("Kafka consumer initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Kafka consumer: {e}")
            raise
    
    async def start_consuming(self):
        """Start consuming messages from Kafka and process them in batches."""
        if not self.consumer:
            await self.initialize_consumer()
        
        self.running = True
        self.logger.info("Starting message consumption with batching enabled...")
        
        try:
            while self.running:
                message_batch = self.consumer.poll(timeout_ms=1000)
                
                if not message_batch:
                    await asyncio.sleep(0.1) # Short sleep to prevent busy-waiting
                else:
                    for topic_partition, messages in message_batch.items():
                        for message in messages:
                            record = await self.process_message(message.value)
                            if record:
                                self.batch.append(record)
                
                # Flush batch if size or time limit is reached
                time_since_flush = time.time() - self.last_flush_time
                # Update batch size gauge
                BATCH_SIZE.set(len(self.batch))

                # Flush batch if size or time limit is reached
                time_since_flush = time.time() - self.last_flush_time
                if (len(self.batch) >= self.config.batch_size or 
                    (time_since_flush >= self.config.flush_interval_seconds and self.batch)):
                    await self._flush_batch()

            # Final flush before shutting down
            await self._flush_batch()

        except Exception as e:
            self.logger.error(f"Error during message consumption: {e}")
            # Ensure final flush on error as well
            await self._flush_batch()
            raise
    
    async def process_message(self, message: Dict[str, Any]) -> Optional[SentimentRecord]:
        """Process a single message and return a SentimentRecord for batching."""
        source = message.get('source', 'unknown')
        with MESSAGE_PROCESSING_LATENCY.labels(source=source).time():
            try:
                content_hash = message.get('content_hash')
                if not content_hash:
                    self.logger.warning("Message missing content_hash, skipping.")
                    ERRORS_TOTAL.labels(source=source, error_type='missing_hash').inc()
                    return None

                # Deduplication checks
                if await self.vector_store.is_duplicate(content_hash):
                    self.logger.debug(f"Skipping duplicate content: {content_hash}")
                    return None
                
                if await self.database.get_sentiment_by_hash(content_hash):
                    self.logger.debug(f"Content already processed: {content_hash}")
                    await self.vector_store.mark_processed(content_hash, {'status': 'existing'})
                    return None

                # Extract content for analysis
                content = message.get('content', {})
                text_to_analyze = self._extract_text_content(source, content)
                if not text_to_analyze:
                    self.logger.warning(f"No text content found for message: {message.get('id')}")
                    ERRORS_TOTAL.labels(source=source, error_type='no_text').inc()
                    return None

                # Perform sentiment analysis
                start_time = time.time()
                sentiment_result = await self.analyzer.analyze(text_to_analyze)
                
                # Create sentiment record
                processing_time_ms = int((time.time() - start_time) * 1000)
                record = SentimentRecord(
                    id=self._generate_id(),
                    source=source,
                    source_id=message.get('source_id', ''),
                    content=content,
                    sentiment=sentiment_result.sentiment,
                    score=sentiment_result.score,
                    confidence=sentiment_result.confidence,
                    entities=sentiment_result.entities,
                    financial_sentiment=sentiment_result.financial_sentiment,
                    vector_hash=content_hash,
                    processed_at=datetime.utcnow(),
                    processing_time_ms=processing_time_ms
                )
                
                return record
                    
            except Exception as e:
                self.error_count += 1
                self.logger.error(f"Error processing message: {e}")
                ERRORS_TOTAL.labels(source=source, error_type='processing_error').inc()
                return None
    
    def _extract_text_content(self, source: str, content: Dict[str, Any]) -> str:
        """Extract text content from message based on the source."""
        if not isinstance(content, dict):
            return str(content)

        if source == 'news':
            headline = content.get('headline', '')
            summary = content.get('summary', '')
            return f"{headline}. {summary}".strip()
        elif source == 'twitter':
            return content.get('text', '')
        elif source == 'truedata':
            # For financial data, we might analyze the symbol or related info
            return content.get('symbol', '')
        else:
            # Fallback for other or unknown sources
            text_fields = ['text', 'content', 'body', 'message', 'description', 'title', 'headline']
            for field in text_fields:
                if field in content and isinstance(content[field], str):
                    return content[field]
            # If no standard field is found, serialize the whole content
            return json.dumps(content)
    
    def _generate_id(self) -> str:
        """Generate unique ID"""
        import uuid
        return str(uuid.uuid4())

    async def _flush_batch(self):
        """Flush the current batch of records to the database."""
        if not self.batch:
            return

        self.logger.info(f"Flushing batch of {len(self.batch)} records...")
        with DATABASE_OPERATION_LATENCY.labels('insert_batch').time():
            success = await self.database.store_sentiments_batch(self.batch)

        if success:
            DATABASE_OPERATIONS_TOTAL.labels(operation='insert_batch', status='success').inc()
            # Post-processing for successfully stored records
            for record in self.batch:
                MESSAGES_PROCESSED_TOTAL.labels(source=record.source).inc()
                await self.vector_store.mark_processed(
                    record.vector_hash,
                    {'status': 'processed', 'sentiment': record.sentiment, 'score': record.score}
                )
                await self.vector_store.store_sentiment_cache(
                    record.vector_hash,
                    {
                        'sentiment': record.sentiment,
                        'score': record.score,
                        'confidence': record.confidence,
                        'entities': record.entities
                    }
                )
            self.processed_count += len(self.batch)
            self.logger.info(f"Successfully flushed {len(self.batch)} records.")
        else:
            DATABASE_OPERATIONS_TOTAL.labels(operation='insert_batch', status='failure').inc()
            self.error_count += len(self.batch)
            self.logger.error(f"Failed to flush batch of {len(self.batch)} records.")

        # Clear the batch and reset the timer
        self.batch.clear()
        self.last_flush_time = time.time()
        
        # Commit offsets after a successful flush
        if self.consumer and success:
            self.consumer.commit_async()
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        try:
            vector_stats = await self.vector_store.get_processing_stats()
            
            return {
                'processed_count': self.processed_count,
                'error_count': self.error_count,
                'is_running': self.running,
                'vector_store_stats': vector_stats
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get stats: {e}")
            return {
                'processed_count': self.processed_count,
                'error_count': self.error_count,
                'is_running': self.running,
                'error': str(e)
            }
    
    async def stop_consuming(self):
        """Stop consuming messages and flush any remaining batch."""
        self.running = False
        self.logger.info("Stopping consumer...")
        
        # Flush any remaining messages
        await self._flush_batch()
        
        if self.consumer:
            self.consumer.close()
            self.logger.info("Kafka consumer stopped")
    
    async def health_check(self) -> bool:
        """Check consumer health"""
        try:
            if not self.consumer:
                return False
            
            # Check if consumer is connected
            topics = self.consumer.topics()
            return len(topics) > 0
            
        except Exception as e:
            self.logger.error(f"Consumer health check failed: {e}")
            return False
