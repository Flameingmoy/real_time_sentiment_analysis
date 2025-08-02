"""Prometheus metrics for monitoring the sentiment analysis service."""

from prometheus_client import Counter, Histogram, Gauge

# Counter for total messages processed
MESSAGES_PROCESSED_TOTAL = Counter(
    'sentiment_analysis_messages_processed_total',
    'Total number of messages processed by the sentiment analysis service',
    ['source']
)

# Counter for total errors
ERRORS_TOTAL = Counter(
    'sentiment_analysis_errors_total',
    'Total number of errors encountered',
    ['source', 'error_type']
)

# Histogram for message processing latency
MESSAGE_PROCESSING_LATENCY = Histogram(
    'sentiment_analysis_message_processing_latency_seconds',
    'Latency of processing a single message',
    ['source'],
    buckets=[0.1, 0.5, 1, 2.5, 5, 10, 30, 60]
)

# Gauge for current batch size
BATCH_SIZE = Gauge(
    'sentiment_analysis_batch_size',
    'Current number of records in the processing batch'
)

# Counter for database operations
DATABASE_OPERATIONS_TOTAL = Counter(
    'sentiment_analysis_db_operations_total',
    'Total number of database operations',
    ['operation', 'status'] # e.g., operation='insert_batch', status='success'
)

# Histogram for database operation latency
DATABASE_OPERATION_LATENCY = Histogram(
    'sentiment_analysis_db_operation_latency_seconds',
    'Latency of database operations',
    ['operation']
)
