-- Logging Database Initialization
-- This database stores system logs and error tracking

-- Create the system_logs table with daily partitioning
CREATE TABLE system_logs (
    id BIGSERIAL,
    level VARCHAR(10) NOT NULL CHECK (level IN ('DEBUG', 'INFO', 'WARN', 'ERROR', 'FATAL')),
    component VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    metadata JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (id, timestamp)
) PARTITION BY RANGE (timestamp);

-- Create indexes for the parent table
CREATE INDEX idx_system_logs_timestamp ON system_logs(timestamp);
CREATE INDEX idx_system_logs_level ON system_logs(level);
CREATE INDEX idx_system_logs_component ON system_logs(component);
CREATE INDEX idx_system_logs_metadata ON system_logs USING GIN(metadata);

-- Create default partition for safety
CREATE TABLE system_logs_default PARTITION OF system_logs DEFAULT;

-- Function to create daily partitions
CREATE OR REPLACE FUNCTION create_daily_log_partition(table_name TEXT, start_date DATE)
RETURNS VOID AS $$
DECLARE
    partition_name TEXT;
    end_date DATE;
BEGIN
    partition_name := table_name || '_y' || EXTRACT(YEAR FROM start_date) || 'm' || LPAD(EXTRACT(MONTH FROM start_date)::TEXT, 2, '0') || 'd' || LPAD(EXTRACT(DAY FROM start_date)::TEXT, 2, '0');
    end_date := start_date + INTERVAL '1 day';
    
    EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF %I FOR VALUES FROM (%L) TO (%L)',
                   partition_name, table_name, start_date, end_date);
    
    -- Create indexes on the partition
    EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %I(timestamp)', 
                   partition_name || '_timestamp_idx', partition_name);
    EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %I(level)', 
                   partition_name || '_level_idx', partition_name);
    EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %I(component)', 
                   partition_name || '_component_idx', partition_name);
END;
$$ LANGUAGE plpgsql;

-- Create partitions for current and next 7 days
DO $$
DECLARE
    i INTEGER;
BEGIN
    FOR i IN 0..7 LOOP
        PERFORM create_daily_log_partition('system_logs', CURRENT_DATE + i);
    END LOOP;
END $$;

-- Error tracking table
CREATE TABLE error_summary (
    id BIGSERIAL PRIMARY KEY,
    component VARCHAR(50) NOT NULL,
    error_type VARCHAR(100) NOT NULL,
    error_count INTEGER NOT NULL DEFAULT 1,
    first_occurrence TIMESTAMP WITH TIME ZONE NOT NULL,
    last_occurrence TIMESTAMP WITH TIME ZONE NOT NULL,
    sample_message TEXT,
    UNIQUE(component, error_type)
);

CREATE INDEX idx_error_summary_component ON error_summary(component);
CREATE INDEX idx_error_summary_type ON error_summary(error_type);
CREATE INDEX idx_error_summary_last_occurrence ON error_summary(last_occurrence);
CREATE INDEX idx_error_summary_count ON error_summary(error_count);

-- Performance metrics table
CREATE TABLE performance_metrics (
    id BIGSERIAL PRIMARY KEY,
    component VARCHAR(50) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(10,4) NOT NULL,
    metric_unit VARCHAR(20),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB
);

CREATE INDEX idx_performance_metrics_component ON performance_metrics(component);
CREATE INDEX idx_performance_metrics_name ON performance_metrics(metric_name);
CREATE INDEX idx_performance_metrics_timestamp ON performance_metrics(timestamp);

-- Function to automatically clean up old logs (configurable retention)
CREATE OR REPLACE FUNCTION cleanup_old_logs(retention_days INTEGER DEFAULT 30)
RETURNS VOID AS $$
DECLARE
    cutoff_date DATE;
    partition_name TEXT;
    partition_record RECORD;
BEGIN
    cutoff_date := CURRENT_DATE - retention_days;
    
    -- Find and drop old partitions
    FOR partition_record IN 
        SELECT schemaname, tablename 
        FROM pg_tables 
        WHERE tablename LIKE 'system_logs_y%' 
        AND schemaname = 'public'
    LOOP
        -- Extract date from partition name and check if it's old enough
        IF partition_record.tablename ~ 'system_logs_y\d{4}m\d{2}d\d{2}' THEN
            EXECUTE format('DROP TABLE IF EXISTS %I', partition_record.tablename);
        END IF;
    END LOOP;
    
    -- Also clean up old performance metrics
    DELETE FROM performance_metrics WHERE timestamp < NOW() - (retention_days || ' days')::INTERVAL;
END;
$$ LANGUAGE plpgsql;

-- Function to update error summary
CREATE OR REPLACE FUNCTION update_error_summary(
    p_component VARCHAR(50),
    p_error_type VARCHAR(100),
    p_message TEXT
)
RETURNS VOID AS $$
BEGIN
    INSERT INTO error_summary (component, error_type, error_count, first_occurrence, last_occurrence, sample_message)
    VALUES (p_component, p_error_type, 1, NOW(), NOW(), p_message)
    ON CONFLICT (component, error_type)
    DO UPDATE SET
        error_count = error_summary.error_count + 1,
        last_occurrence = NOW(),
        sample_message = CASE 
            WHEN error_summary.error_count % 100 = 0 THEN p_message 
            ELSE error_summary.sample_message 
        END;
END;
$$ LANGUAGE plpgsql;

-- Create a view for recent errors
CREATE VIEW recent_errors AS
SELECT 
    component,
    error_type,
    error_count,
    last_occurrence,
    sample_message,
    EXTRACT(EPOCH FROM (NOW() - last_occurrence)) / 3600 as hours_since_last
FROM error_summary
WHERE last_occurrence > NOW() - INTERVAL '24 hours'
ORDER BY last_occurrence DESC;

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO rtsa_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO rtsa_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO rtsa_user;