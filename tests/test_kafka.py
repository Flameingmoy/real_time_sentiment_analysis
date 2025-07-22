#!/usr/bin/env python3
"""
Test script for Kafka producer/consumer functionality
Tests the three main topics: sentiment_analysis_topic, aggregation_topic, alert_topic
"""

import json
import time
import uuid
from datetime import datetime
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
import threading
import signal
import sys

class KafkaTest:
    def __init__(self, bootstrap_servers='localhost:9092'):
        self.bootstrap_servers = bootstrap_servers
        self.topics = ['sentiment_analysis_topic', 'aggregation_topic', 'alert_topic']
        self.test_results = {}
        self.running = True
        
    def create_producer(self):
        """Create Kafka producer with JSON serialization"""
        try:
            producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',
                retries=3,
                retry_backoff_ms=1000
            )
            print("✓ Kafka producer created successfully")
            return producer
        except Exception as e:
            print(f"✗ Failed to create Kafka producer: {e}")
            return None
    
    def create_consumer(self, topic, group_id):
        """Create Kafka consumer for specific topic"""
        try:
            consumer = KafkaConsumer(
                topic,
                bootstrap_servers=self.bootstrap_servers,
                group_id=group_id,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                key_deserializer=lambda k: k.decode('utf-8') if k else None,
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                consumer_timeout_ms=10000  # 10 second timeout
            )
            print(f"✓ Kafka consumer created for topic: {topic}")
            return consumer
        except Exception as e:
            print(f"✗ Failed to create Kafka consumer for {topic}: {e}")
            return None
    
    def test_producer(self, topic):
        """Test message production to a specific topic"""
        producer = self.create_producer()
        if not producer:
            return False
            
        try:
            # Create test message
            test_message = {
                'id': str(uuid.uuid4()),
                'timestamp': datetime.now().isoformat(),
                'source': 'test_producer',
                'content': f'Test message for {topic}',
                'metadata': {
                    'test': True,
                    'topic': topic
                }
            }
            
            # Send message
            future = producer.send(topic, value=test_message, key=test_message['id'])
            record_metadata = future.get(timeout=10)
            
            print(f"✓ Message sent to {topic}")
            print(f"  - Partition: {record_metadata.partition}")
            print(f"  - Offset: {record_metadata.offset}")
            print(f"  - Message ID: {test_message['id']}")
            
            producer.close()
            return True
            
        except KafkaError as e:
            print(f"✗ Failed to send message to {topic}: {e}")
            producer.close()
            return False
        except Exception as e:
            print(f"✗ Unexpected error sending to {topic}: {e}")
            producer.close()
            return False
    
    def test_consumer(self, topic, expected_messages=1):
        """Test message consumption from a specific topic"""
        group_id = f"test_consumer_{topic}_{int(time.time())}"
        consumer = self.create_consumer(topic, group_id)
        if not consumer:
            return False
            
        try:
            messages_received = 0
            print(f"Listening for messages on {topic}...")
            
            for message in consumer:
                if not self.running:
                    break
                    
                print(f"✓ Message received from {topic}")
                print(f"  - Partition: {message.partition}")
                print(f"  - Offset: {message.offset}")
                print(f"  - Key: {message.key}")
                print(f"  - Value: {message.value}")
                
                messages_received += 1
                if messages_received >= expected_messages:
                    break
            
            consumer.close()
            return messages_received > 0
            
        except Exception as e:
            print(f"✗ Failed to consume from {topic}: {e}")
            consumer.close()
            return False
    
    def test_topic_round_trip(self, topic):
        """Test both producer and consumer for a topic"""
        print(f"\n--- Testing {topic} ---")
        
        # Start consumer in background thread
        consumer_result = {'success': False, 'messages': []}
        
        def consumer_thread():
            group_id = f"test_consumer_{topic}_{int(time.time())}"
            consumer = self.create_consumer(topic, group_id)
            if not consumer:
                return
                
            try:
                messages_received = 0
                print(f"Consumer ready for {topic}...")
                
                for message in consumer:
                    if not self.running:
                        break
                        
                    print(f"✓ Message received from {topic}")
                    print(f"  - Partition: {message.partition}")
                    print(f"  - Offset: {message.offset}")
                    print(f"  - Key: {message.key}")
                    print(f"  - Value: {message.value}")
                    
                    consumer_result['messages'].append(message.value)
                    messages_received += 1
                    if messages_received >= 1:
                        consumer_result['success'] = True
                        break
                
                consumer.close()
                
            except Exception as e:
                print(f"✗ Consumer error for {topic}: {e}")
                consumer.close()
        
        consumer_t = threading.Thread(target=consumer_thread)
        consumer_t.daemon = True
        consumer_t.start()
        
        # Wait longer for consumer to be ready
        time.sleep(5)
        
        # Send test message
        producer_success = self.test_producer(topic)
        
        # Wait for consumer to finish
        consumer_t.join(timeout=20)
        
        success = producer_success and consumer_result['success']
        self.test_results[topic] = success
        
        if success:
            print(f"✓ {topic} test PASSED")
        else:
            print(f"✗ {topic} test FAILED")
            if producer_success:
                print("  - Producer worked but consumer failed")
            if not producer_success:
                print("  - Producer failed")
        
        return success
    
    def run_all_tests(self):
        """Run tests for all topics"""
        print("Starting Kafka functionality tests...")
        print(f"Bootstrap servers: {self.bootstrap_servers}")
        print(f"Topics to test: {self.topics}")
        
        # Test each topic
        for topic in self.topics:
            try:
                self.test_topic_round_trip(topic)
            except KeyboardInterrupt:
                print("\nTest interrupted by user")
                self.running = False
                break
            except Exception as e:
                print(f"✗ Unexpected error testing {topic}: {e}")
                self.test_results[topic] = False
        
        # Print summary
        print("\n" + "="*50)
        print("KAFKA TEST SUMMARY")
        print("="*50)
        
        all_passed = True
        for topic, success in self.test_results.items():
            status = "PASS" if success else "FAIL"
            print(f"{topic}: {status}")
            if not success:
                all_passed = False
        
        print("="*50)
        if all_passed:
            print("✓ ALL KAFKA TESTS PASSED")
            return True
        else:
            print("✗ SOME KAFKA TESTS FAILED")
            return False

def signal_handler(sig, frame):
    print('\nTest interrupted by user')
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    
    # Run Kafka tests
    kafka_test = KafkaTest()
    success = kafka_test.run_all_tests()
    
    sys.exit(0 if success else 1)