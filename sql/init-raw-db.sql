-- Raw Data Database Initialization
-- This database stores temporary raw incoming data

-- Create the raw_data table with partitioning support
CREATE TABLE raw_data (
    id BIGSERIAL,
    source VARCHAR(100) NOT NULL,
    source_id VARCHAR(255),
    content JSONB NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (id, timestamp),
    UNIQUE (content_hash, timestamp)
) PARTITION BY RANGE (timestamp);

-- Create indexes for performance
CREATE INDEX idx_raw_data_timestamp ON raw_data(timestamp);
CREATE INDEX idx_raw_data_source ON raw_data(source);
CREATE INDEX idx_raw_data_content_hash ON raw_data(content_hash);
CREATE INDEX idx_raw_data_processed ON raw_data(processed_at) WHERE processed_at IS NULL;

-- Create initial partitions for current month and next month
-- This will be extended by the application as needed
CREATE TABLE raw_data_default PARTITION OF raw_data DEFAULT;

-- Function to create monthly partitions
CREATE OR REPLACE FUNCTION create_monthly_partition(table_name TEXT, start_date DATE)
RETURNS VOID AS $$
DECLARE
    partition_name TEXT;
    end_date DATE;
BEGIN
    partition_name := table_name || '_y' || EXTRACT(YEAR FROM start_date) || 'm' || LPAD(EXTRACT(MONTH FROM start_date)::TEXT, 2, '0');
    end_date := start_date + INTERVAL '1 month';
    
    EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF %I FOR VALUES FROM (%L) TO (%L)',
                   partition_name, table_name, start_date, end_date);
END;
$$ LANGUAGE plpgsql;

-- Create partitions for current and next few months
SELECT create_monthly_partition('raw_data', DATE_TRUNC('month', CURRENT_DATE)::DATE);
SELECT create_monthly_partition('raw_data', (DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month')::DATE);
SELECT create_monthly_partition('raw_data', (DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '2 months')::DATE);

-- Create a function to automatically purge old data (7-day retention)
CREATE OR REPLACE FUNCTION cleanup_old_raw_data()
RETURNS VOID AS $$
BEGIN
    DELETE FROM raw_data 
    WHERE created_at < NOW() - INTERVAL '7 days';
END;
$$ LANGUAGE plpgsql;

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO rtsa_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO rtsa_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO rtsa_user;