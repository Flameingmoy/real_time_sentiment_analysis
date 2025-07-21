-- Analytics Database Initialization
-- This database stores processed sentiment analysis results

-- Create the sentiment_results table
CREATE TABLE sentiment_results (
    id BIGSERIAL PRIMARY KEY,
    source_id VARCHAR(255) NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    sentiment_score DECIMAL(5,4) NOT NULL CHECK (sentiment_score >= -1 AND sentiment_score <= 1),
    sentiment_label VARCHAR(20) NOT NULL CHECK (sentiment_label IN ('positive', 'negative', 'neutral')),
    confidence_score DECIMAL(5,4) NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 1),
    entities JSONB,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Performance indexes
CREATE INDEX idx_sentiment_timestamp ON sentiment_results(timestamp);
CREATE INDEX idx_sentiment_source_type ON sentiment_results(source_type);
CREATE INDEX idx_sentiment_label ON sentiment_results(sentiment_label);
CREATE INDEX idx_sentiment_score ON sentiment_results(sentiment_score);
CREATE INDEX idx_sentiment_entities ON sentiment_results USING GIN(entities);
CREATE INDEX idx_sentiment_content_hash ON sentiment_results(content_hash);

-- Composite indexes for common queries
CREATE INDEX idx_sentiment_source_timestamp ON sentiment_results(source_type, timestamp);
CREATE INDEX idx_sentiment_label_timestamp ON sentiment_results(sentiment_label, timestamp);

-- Aggregation views for dashboards
CREATE MATERIALIZED VIEW hourly_sentiment_summary AS
SELECT 
    DATE_TRUNC('hour', timestamp) as hour,
    source_type,
    sentiment_label,
    COUNT(*) as count,
    AVG(sentiment_score) as avg_score,
    AVG(confidence_score) as avg_confidence,
    MIN(sentiment_score) as min_score,
    MAX(sentiment_score) as max_score
FROM sentiment_results 
GROUP BY DATE_TRUNC('hour', timestamp), source_type, sentiment_label;

CREATE UNIQUE INDEX idx_hourly_sentiment_summary ON hourly_sentiment_summary(hour, source_type, sentiment_label);

-- Daily sentiment summary for historical analysis
CREATE MATERIALIZED VIEW daily_sentiment_summary AS
SELECT 
    DATE_TRUNC('day', timestamp) as day,
    source_type,
    sentiment_label,
    COUNT(*) as count,
    AVG(sentiment_score) as avg_score,
    AVG(confidence_score) as avg_confidence,
    STDDEV(sentiment_score) as score_stddev
FROM sentiment_results 
GROUP BY DATE_TRUNC('day', timestamp), source_type, sentiment_label;

CREATE UNIQUE INDEX idx_daily_sentiment_summary ON daily_sentiment_summary(day, source_type, sentiment_label);

-- Source volume metrics view
CREATE MATERIALIZED VIEW source_volume_metrics AS
SELECT 
    DATE_TRUNC('hour', timestamp) as hour,
    source_type,
    COUNT(*) as message_count,
    COUNT(DISTINCT source_id) as unique_sources,
    AVG(confidence_score) as avg_confidence
FROM sentiment_results 
GROUP BY DATE_TRUNC('hour', timestamp), source_type;

CREATE UNIQUE INDEX idx_source_volume_metrics ON source_volume_metrics(hour, source_type);

-- Function to refresh materialized views
CREATE OR REPLACE FUNCTION refresh_sentiment_views()
RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY hourly_sentiment_summary;
    REFRESH MATERIALIZED VIEW CONCURRENTLY daily_sentiment_summary;
    REFRESH MATERIALIZED VIEW CONCURRENTLY source_volume_metrics;
END;
$$ LANGUAGE plpgsql;

-- Entity extraction summary for NER analysis
CREATE TABLE entity_summary (
    id BIGSERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,
    entity_value VARCHAR(255) NOT NULL,
    sentiment_label VARCHAR(20) NOT NULL,
    occurrence_count INTEGER NOT NULL DEFAULT 1,
    avg_sentiment_score DECIMAL(5,4) NOT NULL,
    first_seen TIMESTAMP WITH TIME ZONE NOT NULL,
    last_seen TIMESTAMP WITH TIME ZONE NOT NULL,
    UNIQUE(entity_type, entity_value, sentiment_label)
);

CREATE INDEX idx_entity_summary_type ON entity_summary(entity_type);
CREATE INDEX idx_entity_summary_value ON entity_summary(entity_value);
CREATE INDEX idx_entity_summary_sentiment ON entity_summary(sentiment_label);
CREATE INDEX idx_entity_summary_last_seen ON entity_summary(last_seen);

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO rtsa_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO rtsa_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO rtsa_user;