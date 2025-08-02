"""Configuration management for sentiment analysis service"""

import os
from typing import Dict, Any
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class DatabaseConfig:
    host: str
    port: int
    database: str
    user: str
    password: str
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30

@dataclass
class KafkaConfig:
    bootstrap_servers: list
    group_id: str
    topics: Dict[str, str]
    auto_offset_reset: str = 'earliest'
    enable_auto_commit: bool = True
    max_poll_records: int = 100
    session_timeout_ms: int = 30000
    heartbeat_interval_ms: int = 3000
    batch_size: int = 100
    flush_interval_seconds: int = 10

@dataclass
class RedisConfig:
    host: str
    port: int
    password: str = None
    db: int = 0
    decode_responses: bool = True
    socket_timeout: int = 30
    socket_connect_timeout: int = 30
    index_name: str = "rtsa-embeddings"
    embedding_dim: int = 1024

@dataclass
class OllamaConfig:
    host: str
    port: int
    model: str
    timeout: int = 300
    max_retries: int = 3
    retry_delay: float = 1.0

@dataclass
class ServerConfig:
    host: str
    port: int
    debug: bool = False
    log_level: str = 'INFO'

class Config:
    """Main configuration class"""

    def __init__(self):
        self.database_config = self._load_database_config()
        self.kafka_config = self._load_kafka_config()
        self.redis_config = self._load_redis_config()
        self.ollama_config = self._load_ollama_config()
        self.server_config = self._load_server_config()
        self.validate()

    def _load_database_config(self) -> DatabaseConfig:
        """Load database configuration"""
        return DatabaseConfig(
            host=os.getenv('ANALYTICS_DB_HOST', 'localhost'),
            port=int(os.getenv('ANALYTICS_DB_PORT', 5433)),
            database=os.getenv('ANALYTICS_DB_NAME', 'rtsa_analytics'),
            user=os.getenv('ANALYTICS_DB_USER', 'rtsa_user'),
            password=os.getenv('ANALYTICS_DB_PASSWORD', 'rtsa_password'),
            pool_size=int(os.getenv('DB_POOL_SIZE', 10)),
            max_overflow=int(os.getenv('DB_MAX_OVERFLOW', 20)),
            pool_timeout=int(os.getenv('DB_POOL_TIMEOUT', 30))
        )

    def _load_kafka_config(self) -> KafkaConfig:
        """Load Kafka configuration"""
        brokers = os.getenv('KAFKA_BROKERS', 'localhost:9092').split(',')
        return KafkaConfig(
            bootstrap_servers=brokers,
            group_id=os.getenv('KAFKA_CONSUMER_GROUP', 'sentiment-analysis-group'),
            topics={
                'sentiment_analysis': os.getenv('KAFKA_TOPIC_SENTIMENT_ANALYSIS', 'sentiment_analysis_topic'),
                'aggregation': os.getenv('KAFKA_TOPIC_AGGREGATION', 'aggregation_topic'),
                'alert': os.getenv('KAFKA_TOPIC_ALERT', 'alert_topic')
            },
            auto_offset_reset=os.getenv('KAFKA_AUTO_OFFSET_RESET', 'earliest'),
            enable_auto_commit=os.getenv('KAFKA_ENABLE_AUTO_COMMIT', 'true').lower() == 'true',
            max_poll_records=int(os.getenv('KAFKA_MAX_POLL_RECORDS', 100)),
            session_timeout_ms=int(os.getenv('KAFKA_SESSION_TIMEOUT_MS', 30000)),
            heartbeat_interval_ms=int(os.getenv('KAFKA_HEARTBEAT_INTERVAL_MS', 3000)),
            batch_size=int(os.getenv('KAFKA_BATCH_SIZE', 100)),
            flush_interval_seconds=int(os.getenv('KAFKA_FLUSH_INTERVAL_SECONDS', 10))
        )

    def _load_redis_config(self) -> RedisConfig:
        """Load Redis configuration"""
        return RedisConfig(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6380)),
            password=os.getenv('REDIS_PASSWORD', None),
            db=int(os.getenv('REDIS_DB', 0)),
            socket_timeout=int(os.getenv('REDIS_SOCKET_TIMEOUT', 30)),
            socket_connect_timeout=int(os.getenv('REDIS_SOCKET_CONNECT_TIMEOUT', 30)),
            index_name=os.getenv('REDIS_INDEX_NAME', 'rtsa-embeddings'),
            embedding_dim=int(os.getenv('REDIS_EMBEDDING_DIM', 1024))
        )

    def _load_ollama_config(self) -> OllamaConfig:
        """Load Ollama configuration"""
        from urllib.parse import urlparse
        ollama_url = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        parsed_url = urlparse(ollama_url)
        return OllamaConfig(
            host=parsed_url.hostname,
            port=parsed_url.port,
            model=os.getenv('OLLAMA_MODEL', 'granite3.3:8b'),
            timeout=int(os.getenv('OLLAMA_TIMEOUT', 300)),
            max_retries=int(os.getenv('OLLAMA_MAX_RETRIES', 3)),
            retry_delay=float(os.getenv('OLLAMA_RETRY_DELAY', 1.0))
        )

    def _load_server_config(self) -> Dict[str, Any]:
        """Load server configuration"""
        return {
            'host': os.getenv('SERVICE_HOST', '0.0.0.0'),
            'port': int(os.getenv('SERVICE_PORT', 8081)),
            'debug': os.getenv('DEBUG', 'false').lower() == 'true',
            'log_level': os.getenv('LOG_LEVEL', 'INFO')
        }

    def validate(self) -> bool:
        """Validate configuration"""
        try:
            required_vars = [
                'ANALYTICS_DB_HOST', 'ANALYTICS_DB_PORT', 'ANALYTICS_DB_NAME', 'ANALYTICS_DB_USER', 'ANALYTICS_DB_PASSWORD',
                'KAFKA_BROKERS', 'KAFKA_CONSUMER_GROUP',
                'REDIS_HOST', 'REDIS_PORT',
                'OLLAMA_HOST', 'OLLAMA_MODEL'
            ]
            missing_vars = [var for var in required_vars if not os.getenv(var)]
            if missing_vars:
                raise ValueError(f"Missing required environment variables: {missing_vars}")
            return True
        except Exception as e:
            # Assuming logger is configured elsewhere or using print for bootstrap issues
            print(f"Configuration validation failed: {e}")
            return False
