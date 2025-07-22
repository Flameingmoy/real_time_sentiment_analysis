#!/bin/bash

# Wait for Kafka to be ready
echo "Waiting for Kafka to be ready..."
until kafka-topics --bootstrap-server $KAFKA_BROKER --list > /dev/null 2>&1; do
    echo "Kafka not ready yet, waiting..."
    sleep 5
done

echo "Kafka is ready. Creating topics..."

# Create sentiment_analysis_topic
kafka-topics --bootstrap-server $KAFKA_BROKER \
    --create \
    --topic sentiment_analysis_topic \
    --partitions 3 \
    --replication-factor 1 \
    --config retention.ms=604800000 \
    --config segment.ms=86400000 \
    --if-not-exists

# Create aggregation_topic
kafka-topics --bootstrap-server $KAFKA_BROKER \
    --create \
    --topic aggregation_topic \
    --partitions 2 \
    --replication-factor 1 \
    --config retention.ms=604800000 \
    --config segment.ms=86400000 \
    --if-not-exists

# Create alert_topic
kafka-topics --bootstrap-server $KAFKA_BROKER \
    --create \
    --topic alert_topic \
    --partitions 1 \
    --replication-factor 1 \
    --config retention.ms=2592000000 \
    --config segment.ms=86400000 \
    --if-not-exists

echo "Topics created successfully!"

# List all topics to verify
echo "Current topics:"
kafka-topics --bootstrap-server $KAFKA_BROKER --list

# Describe topics to show configuration
echo "Topic configurations:"
kafka-topics --bootstrap-server $KAFKA_BROKER --describe --topic sentiment_analysis_topic
kafka-topics --bootstrap-server $KAFKA_BROKER --describe --topic aggregation_topic
kafka-topics --bootstrap-server $KAFKA_BROKER --describe --topic alert_topic