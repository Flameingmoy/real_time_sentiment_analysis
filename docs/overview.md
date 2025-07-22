# Real-time Sentiment Analysis MVP - Project Overview

## Project Purpose
RTSA (Real-time Sentiment Analysis) is a scalable pipeline designed to process financial, economic, and geopolitical data streams and provide actionable sentiment insights for algorithmic trading decisions. This MVP focuses on core functionality without advanced security, monitoring, or deployment considerations.

## MVP Scope
The MVP will demonstrate the core sentiment analysis pipeline with the following data sources:
- Financial news feeds (simulated/API-based)
- Economic indicators and reports
- Social media sentiment (Twitter/Reddit APIs)
- Market data and price movements

## Core Architecture Components

### 1. Data Ingestion Layer
**Technology:** Golang
- High-performance HTTP server for webhook handling
- Gin framework for HTTP routing
- Rate limiting and basic error handling
- Data validation and sanitization
- Concurrent processing with goroutines

**Data Sources:**
- TrueData API integration
- News APIs (Reuters, Bloomberg alternatives)
- Social Media APIs (Twitter API v2, Reddit API)
- Economic Data APIs (Fed APIs, ECB APIs)

### 2. Data Storage Layer

**PostgreSQL Database 1 (Raw Data Ingestion):**
- Purpose: Raw data ingestion and temporary storage
- Schema: JSONB columns for flexible data structure
- Basic indexing on source, timestamp, and content hash
- 7-day data retention

**Apache Kafka Message Queue:**
- Purpose: Asynchronous processing and load balancing
- Topics:
  - `sentiment_analysis_topic`: Data awaiting sentiment analysis
  - `aggregation_topic`: Data ready for aggregation
  - `alert_topic`: Urgent sentiment changes
- Basic Kafka configuration with persistence and partitioning

**Redis Vector Store:**
- Purpose: Semantic search and similarity matching
- Text embeddings storage for efficient similarity searches
- Content deduplication using vector similarity
- RedisSearch module with vector similarity search

### 3. Processing Layer
**Sentiment Analysis Service:**
- Model: IBM Granite 3.3 2b (lighter version for MVP)
- Implementation: Python microservice using HuggingFace Transformers
- Features:
  - Multi-class sentiment classification (positive, negative, neutral)
  - Confidence scoring
  - Basic entity extraction for financial instruments
  - Batch processing for efficiency

**Processing Pipeline:**
- Text preprocessing and cleaning
- Language detection and filtering
- Duplicate detection using vector similarity
- Sentiment scoring and classification
- Entity recognition and linking

### 4. Data Persistence Layer
**PostgreSQL Database 2 (Analytics):**
- Purpose: Structured storage of processed sentiment data
- Schema:
```sql
CREATE TABLE sentiment_results (
    id BIGSERIAL PRIMARY KEY,
    source_id VARCHAR(255) NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    sentiment_score DECIMAL(3,2) NOT NULL,
    sentiment_label VARCHAR(20) NOT NULL,
    confidence_score DECIMAL(3,2) NOT NULL,
    entities JSONB,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**PostgreSQL Database 3 (Logging):**
- Purpose: Basic system logging
- Schema: Simple daily partitioned tables for log entries
- Tables:
  - `system_logs_YYYY_MM_DD`: Application logs
  - `error_logs_YYYY_MM_DD`: Error tracking

### 5. Visualization Layer
**Grafana:**
- Purpose: Interactive dashboards and real-time analytics
- Basic dashboards:
  - Real-time sentiment trends by asset class
  - Source volume metrics
  - Historical sentiment analysis
  - System performance metrics
- Features:
  - Real-time data refresh (30-second intervals)
  - Direct PostgreSQL data source connections
  - Custom SQL queries for analytics
  - Alerting capabilities for sentiment thresholds

## Technology Stack

| Layer | Technology | Purpose | Language |
|-------|------------|---------|----------|
| Data Sources | TrueData API | Real-time financial data | JSON/WebSocket |
| Ingestion | Golang | High-performance data ingestion | Go |
| Message Queue | Apache Kafka | Asynchronous task processing | Kafka Protocol |
| Vector Database | Redis Vector | Semantic search | Redis Commands |
| Raw Storage | PostgreSQL-1 | Raw data persistence | SQL |
| Analytics Storage | PostgreSQL-2 | Processed sentiment data | SQL |
| Logging Storage | PostgreSQL-3 | System logs | SQL |
| AI/ML | IBM Granite 3.3 | Sentiment analysis | Python/REST API |
| Visualization | Grafana | Dashboards | PromQL/SQL |

## Data Flow

### 1. Ingestion Flow
```
External Sources → Webhooks → Golang Ingestion Service → PostgreSQL-1 → Kafka Topics
```

### 2. Processing Flow
```
Kafka Topics → Python Sentiment Service → IBM Granite Model → PostgreSQL-2 → Vector Store (Redis)
```

### 3. Visualization Flow
```
PostgreSQL-2 → Grafana → Dashboard → Trading Alerts
```

### 4. Logging Flow
```
All Components → Structured Logging → PostgreSQL-3
```

## MVP Performance Targets

### Throughput Requirements
- Data Ingestion: <500ms per data source
- Ingestion Rate: 100+ messages/second
- Vector Search: <100ms per search
- Sentiment Analysis: <10 seconds per analysis
- Storage: 1GB of new data per day
- Dashboard Updates: <500ms for dashboard queries

### Basic Scalability
- Application: Single-instance services with basic horizontal scaling capability
- Database: Single PostgreSQL instances with basic connection pooling
- Cache: Single Redis instance with basic configuration
- Message Queue: Single Kafka broker with basic topic configuration
- Vector Store: Single Redis instance for vector operations

## MVP Database Schema

### Raw Data Table (PostgreSQL-1)
```sql
CREATE TABLE raw_data (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(100) NOT NULL,
    source_id VARCHAR(255),
    content JSONB NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_raw_data_timestamp ON raw_data(timestamp);
CREATE INDEX idx_raw_data_source ON raw_data(source);
CREATE INDEX idx_raw_data_content_hash ON raw_data(content_hash);
```

### System Logs Table (PostgreSQL-3)
```sql
CREATE TABLE system_logs (
    id BIGSERIAL PRIMARY KEY,
    level VARCHAR(10) NOT NULL,
    component VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    metadata JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_system_logs_timestamp ON system_logs(timestamp);
CREATE INDEX idx_system_logs_level ON system_logs(level);
CREATE INDEX idx_system_logs_component ON system_logs(component);
```

## MVP Limitations
- Single-node deployment
- Basic error handling
- No advanced security measures
- No monitoring/alerting system
- No disaster recovery
- No automated testing
- Basic logging
- No CI/CD pipeline
- No load balancing
- No advanced caching strategies

## Success Criteria for MVP
1. Successfully ingest data from at least 2 different sources
2. Process sentiment analysis on ingested data
3. Store processed results in database
4. Display real-time results in Superset dashboard
5. Handle at least 50 messages per second
6. Demonstrate end-to-end data flow
7. Basic error logging and handling
8. Vector similarity search working for deduplication