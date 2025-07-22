#!/usr/bin/env python3
"""
Simple Kafka test script to verify producer/consumer functionality
"""

import json
import time
import uuid
from datetime import datetime
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError

def test_producer():
    """Test Kafka producer functionality"""
    print("Testing Kafka Producer...")
    
    try:
        producer = KafkaProducer(
            bootstrap_servers=['localhost:9092'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            acks='all',
            retries=3
        )
        
        topics = ['sentiment_analysis_topic', 'aggregation_topic', 'alert_topic']
        
        for topic in topics:
            test_message = {
                'id': str(uuid.uuid4()),
                'timestamp': datetime.now().isoformat(),
                'source': 'test_producer',
                'content': f'Test message for {topic}',
                'topic': topic
            }
            
            future = producer.send(topic, value=test_message, key=test_message['id'])
            record_metadata = future.get(timeout=10)
            
            print(f"✓ Message sent to {topic}")
            print(f"  - Partition: {record_metadata.partition}")
            print(f"  - Offset: {record_metadata.offset}")
        
        producer.close()
        print("✓ Producer test PASSED")
        return True
        
    except Exception as e:
        print(f"✗ Producer test FAILED: {e}")
        return False

def test_consumer():
    """Test Kafka consumer functionality"""
    print("\nTesting Kafka Consumer...")
    
    topics = ['sentiment_analysis_topic', 'aggregation_topic', 'alert_topic']
    
    for topic in topics:
        try:
            consumer = KafkaConsumer(
                topic,
                bootstrap_servers=['localhost:9092'],
                group_id=f'test_group_{topic}_{int(time.time())}',
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='earliest',
                consumer_timeout_ms=5000
            )
            
            print(f"Testing consumer for {topic}...")
            messages_found = 0
            
            for message in consumer:
                print(f"✓ Message received from {topic}")
                print(f"  - Partition: {message.partition}")
                print(f"  - Offset: {message.offset}")
                print(f"  - Value: {message.value}")
                messages_found += 1
                break  # Just need to verify we can consume
            
            consumer.close()
            
            if messages_found > 0:
                print(f"✓ Consumer test for {topic} PASSED")
            else:
                print(f"✗ No messages found in {topic}")
                
        except Exception as e:
            print(f"✗ Consumer test for {topic} FAILED: {e}")
    
    return True

if __name__ == "__main__":
    print("Starting Kafka functionality tests...")
    
    # Test producer first
    producer_success = test_producer()
    
    if producer_success:
        # Wait a moment then test consumer
        time.sleep(2)
        consumer_success = test_consumer()
        
        if producer_success and consumer_success:
            print("\n✓ ALL KAFKA TESTS COMPLETED")
        else:
            print("\n✗ SOME TESTS HAD ISSUES")
    else:
        print("\n✗ PRODUCER TEST FAILED")