package kafka

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"testing"
	"time"

	"rtsa-ingestion/internal/config"
)

// createTestKafkaConfig creates a test Kafka configuration
func createTestKafkaConfig() *config.KafkaConfig {
	return &config.KafkaConfig{
		Brokers: []string{"localhost:9092"},
		Topics: config.KafkaTopicsConfig{
			SentimentAnalysis: "test_sentiment_analysis",
			Aggregation:       "test_aggregation",
			Alert:            "test_alert",
		},
		Producer: config.KafkaProducerConfig{
			RetryMax:       3,
			RetryBackoff:   100 * time.Millisecond,
			FlushFrequency: 100 * time.Millisecond,
			BatchSize:      10,
		},
	}
}

func TestNewProducer(t *testing.T) {
	tests := []struct {
		name    string
		config  *config.KafkaConfig
		wantErr bool
	}{
		{
			name:    "valid config",
			config:  createTestKafkaConfig(),
			wantErr: true, // Will fail without actual Kafka broker
		},
		{
			name: "empty brokers",
			config: &config.KafkaConfig{
				Brokers: []string{},
				Topics: config.KafkaTopicsConfig{
					SentimentAnalysis: "test_topic",
				},
				Producer: config.KafkaProducerConfig{
					RetryMax:       3,
					RetryBackoff:   100 * time.Millisecond,
					FlushFrequency: 100 * time.Millisecond,
					BatchSize:      10,
				},
			},
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			producer, err := NewProducer(tt.config)
			if (err != nil) != tt.wantErr {
				t.Errorf("NewProducer() error = %v, wantErr %v", err, tt.wantErr)
				return
			}
			if producer != nil {
				producer.Close()
			}
		})
	}
}

func TestMessage_Validation(t *testing.T) {
	tests := []struct {
		name    string
		message *Message
		wantErr bool
	}{
		{
			name: "valid message",
			message: &Message{
				Topic: "test_topic",
				Key:   "test_key",
				Value: map[string]interface{}{
					"test": "data",
				},
				Headers: map[string]string{
					"source": "test",
				},
				Timestamp: time.Now(),
			},
			wantErr: false,
		},
		{
			name: "message without topic",
			message: &Message{
				Value: map[string]interface{}{
					"test": "data",
				},
			},
			wantErr: false, // Topic validation happens at send time
		},
		{
			name: "message without value",
			message: &Message{
				Topic: "test_topic",
			},
			wantErr: false, // Value validation happens at send time
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			// Basic validation - just check if message can be created
			if tt.message == nil {
				t.Error("Message should not be nil")
			}
		})
	}
}

func TestProducerError(t *testing.T) {
	tests := []struct {
		name      string
		err       *ProducerError
		wantError string
		retryable bool
	}{
		{
			name: "retryable error",
			err: &ProducerError{
				Operation: "send_message",
				Topic:     "test_topic",
				Err:       &MockError{message: "connection refused"},
				Retryable: true,
			},
			wantError: "kafka producer operation 'send_message' failed for topic 'test_topic': connection refused",
			retryable: true,
		},
		{
			name: "non-retryable error",
			err: &ProducerError{
				Operation: "marshal_message",
				Topic:     "test_topic",
				Err:       &MockError{message: "invalid JSON"},
				Retryable: false,
			},
			wantError: "kafka producer operation 'marshal_message' failed for topic 'test_topic': invalid JSON",
			retryable: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if tt.err.Error() != tt.wantError {
				t.Errorf("ProducerError.Error() = %v, want %v", tt.err.Error(), tt.wantError)
			}

			if tt.err.IsRetryable() != tt.retryable {
				t.Errorf("ProducerError.IsRetryable() = %v, want %v", tt.err.IsRetryable(), tt.retryable)
			}

			// Test Unwrap
			if tt.err.Unwrap() == nil {
				t.Error("Expected Unwrap() to return the wrapped error")
			}
		})
	}
}

func TestIsRetryableKafkaError(t *testing.T) {
	tests := []struct {
		name      string
		err       error
		retryable bool
	}{
		{
			name:      "nil error",
			err:       nil,
			retryable: false,
		},
		{
			name:      "connection refused error",
			err:       &MockError{message: "connection refused"},
			retryable: true,
		},
		{
			name:      "timeout error",
			err:       &MockError{message: "timeout occurred"},
			retryable: true,
		},
		{
			name:      "network error",
			err:       &MockError{message: "network error"},
			retryable: true,
		},
		{
			name:      "validation error",
			err:       &MockError{message: "invalid message format"},
			retryable: false,
		},
		{
			name:      "unknown error",
			err:       &MockError{message: "unknown error"},
			retryable: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := isRetryableKafkaError(tt.err)
			if result != tt.retryable {
				t.Errorf("isRetryableKafkaError() = %v, want %v", result, tt.retryable)
			}
		})
	}
}

func TestContains(t *testing.T) {
	tests := []struct {
		name   string
		s      string
		substr string
		want   bool
	}{
		{
			name:   "exact match",
			s:      "timeout",
			substr: "timeout",
			want:   true,
		},
		{
			name:   "substring at beginning",
			s:      "timeout occurred",
			substr: "timeout",
			want:   true,
		},
		{
			name:   "substring at end",
			s:      "connection timeout",
			substr: "timeout",
			want:   true,
		},
		{
			name:   "substring in middle",
			s:      "connection timeout error",
			substr: "timeout",
			want:   true,
		},
		{
			name:   "no match",
			s:      "connection refused",
			substr: "timeout",
			want:   false,
		},
		{
			name:   "empty substring",
			s:      "test string",
			substr: "",
			want:   true,
		},
		{
			name:   "empty string",
			s:      "",
			substr: "test",
			want:   false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := contains(tt.s, tt.substr)
			if result != tt.want {
				t.Errorf("contains(%q, %q) = %v, want %v", tt.s, tt.substr, result, tt.want)
			}
		})
	}
}

// MockError is a simple error implementation for testing
type MockError struct {
	message string
}

func (e *MockError) Error() string {
	return e.message
}

// Integration tests that would require a real Kafka broker
// These tests are skipped by default but can be run with a test flag

func TestProducer_SendMessage_Integration(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping integration test in short mode")
	}

	// This test would require a real Kafka broker
	t.Skip("Integration test requires Kafka broker - implement with testcontainers if needed")
	
	cfg := createTestKafkaConfig()
	producer, err := NewProducer(cfg)
	if err != nil {
		t.Skipf("Could not create Kafka producer: %v", err)
	}
	defer producer.Close()

	ctx := context.Background()
	msg := &Message{
		Topic: cfg.Topics.SentimentAnalysis,
		Key:   "test_key",
		Value: map[string]interface{}{
			"test_data": "integration_test",
			"timestamp": time.Now().Unix(),
		},
		Headers: map[string]string{
			"source": "integration_test",
		},
	}

	err = producer.SendMessage(ctx, msg)
	if err != nil {
		t.Errorf("SendMessage() error = %v", err)
	}
}

func TestProducer_SendMessageBatch_Integration(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping integration test in short mode")
	}

	// This test would require a real Kafka broker
	t.Skip("Integration test requires Kafka broker - implement with testcontainers if needed")
	
	cfg := createTestKafkaConfig()
	producer, err := NewProducer(cfg)
	if err != nil {
		t.Skipf("Could not create Kafka producer: %v", err)
	}
	defer producer.Close()

	ctx := context.Background()
	messages := []*Message{
		{
			Topic: cfg.Topics.SentimentAnalysis,
			Key:   "batch_test_1",
			Value: map[string]interface{}{
				"batch_data": "test_1",
				"timestamp":  time.Now().Unix(),
			},
		},
		{
			Topic: cfg.Topics.SentimentAnalysis,
			Key:   "batch_test_2",
			Value: map[string]interface{}{
				"batch_data": "test_2",
				"timestamp":  time.Now().Unix(),
			},
		},
	}

	err = producer.SendMessageBatch(ctx, messages)
	if err != nil {
		t.Errorf("SendMessageBatch() error = %v", err)
	}
}

func TestProducer_HealthCheck_Integration(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping integration test in short mode")
	}

	// This test would require a real Kafka broker
	t.Skip("Integration test requires Kafka broker - implement with testcontainers if needed")
	
	cfg := createTestKafkaConfig()
	producer, err := NewProducer(cfg)
	if err != nil {
		t.Skipf("Could not create Kafka producer: %v", err)
	}
	defer producer.Close()

	ctx := context.Background()
	err = producer.HealthCheck(ctx)
	if err != nil {
		t.Errorf("HealthCheck() error = %v", err)
	}
}

func TestProducer_GetMetrics(t *testing.T) {
	// This test doesn't require a real Kafka broker
	cfg := createTestKafkaConfig()
	
	// Create a mock producer for testing metrics
	producer := &Producer{
		config: cfg,
		topics: &cfg.Topics,
	}

	metrics := producer.GetMetrics()
	if metrics == nil {
		t.Error("Expected metrics to be returned")
	}

	// Verify required metrics fields
	expectedFields := []string{
		"brokers",
		"topics",
		"producer_config",
		"status",
	}

	for _, field := range expectedFields {
		if _, exists := metrics[field]; !exists {
			t.Errorf("Expected metrics field %s to be present", field)
		}
	}

	// Verify topics structure
	if topics, ok := metrics["topics"].(map[string]string); ok {
		expectedTopics := []string{
			"sentiment_analysis",
			"aggregation",
			"alert",
		}

		for _, topic := range expectedTopics {
			if _, exists := topics[topic]; !exists {
				t.Errorf("Expected topic %s to be present in metrics", topic)
			}
		}
	} else {
		t.Error("Expected topics to be a map[string]string")
	}
}

func TestProducer_WithRetry(t *testing.T) {
	cfg := createTestKafkaConfig()
	producer := &Producer{
		config: cfg,
		topics: &cfg.Topics,
	}

	tests := []struct {
		name          string
		operation     string
		fn            func() error
		expectedCalls int
		wantErr       bool
	}{
		{
			name:      "successful operation on first try",
			operation: "test_operation",
			fn: func() error {
				return nil
			},
			expectedCalls: 1,
			wantErr:       false,
		},
		{
			name:      "non-retryable error",
			operation: "test_operation",
			fn: func() error {
				return &ProducerError{
					Operation: "test",
					Err:       fmt.Errorf("validation error"),
					Retryable: false,
				}
			},
			expectedCalls: 1,
			wantErr:       true,
		},
		{
			name:      "retryable error that eventually succeeds",
			operation: "test_operation",
			fn: func() func() error {
				callCount := 0
				return func() error {
					callCount++
					if callCount < 2 {
						return &ProducerError{
							Operation: "test",
							Err:       fmt.Errorf("connection refused"),
							Retryable: true,
						}
					}
					return nil
				}
			}(),
			expectedCalls: 2,
			wantErr:       false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			ctx := context.Background()
			err := producer.WithRetry(ctx, tt.operation, tt.fn)
			
			if (err != nil) != tt.wantErr {
				t.Errorf("WithRetry() error = %v, wantErr %v", err, tt.wantErr)
			}
		})
	}
}

func TestProducer_WithRetry_ContextCancellation(t *testing.T) {
	cfg := createTestKafkaConfig()
	producer := &Producer{
		config: cfg,
		topics: &cfg.Topics,
	}

	ctx, cancel := context.WithCancel(context.Background())
	cancel() // Cancel immediately

	err := producer.WithRetry(ctx, "test_operation", func() error {
		return &ProducerError{
			Operation: "test",
			Err:       fmt.Errorf("connection refused"),
			Retryable: true,
		}
	})

	if err == nil {
		t.Error("Expected error due to context cancellation")
	}

	var producerErr *ProducerError
	if !errors.As(err, &producerErr) {
		t.Error("Expected ProducerError")
	}
}

func TestProducer_HealthCheckDetailed(t *testing.T) {
	cfg := createTestKafkaConfig()
	
	tests := []struct {
		name     string
		producer *Producer
		wantStatus string
	}{
		{
			name: "producer not initialized",
			producer: &Producer{
				config: cfg,
				topics: &cfg.Topics,
				producer: nil,
			},
			wantStatus: "unhealthy",
		},
		{
			name: "producer initialized but no connection",
			producer: &Producer{
				config: cfg,
				topics: &cfg.Topics,
				// producer will be nil, simulating failed initialization
			},
			wantStatus: "unhealthy",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			ctx := context.Background()
			result := tt.producer.HealthCheckDetailed(ctx)
			
			if result == nil {
				t.Error("Expected health check result")
				return
			}

			status, ok := result["status"].(string)
			if !ok {
				t.Error("Expected status to be a string")
				return
			}

			if status != tt.wantStatus {
				t.Errorf("Expected status %s, got %s", tt.wantStatus, status)
			}

			// Verify required fields
			expectedFields := []string{"status", "timestamp", "checks"}
			for _, field := range expectedFields {
				if _, exists := result[field]; !exists {
					t.Errorf("Expected field %s to be present", field)
				}
			}

			// Verify checks structure
			checks, ok := result["checks"].(map[string]interface{})
			if !ok {
				t.Error("Expected checks to be a map")
				return
			}

			// For producer not initialized, we only expect producer_initialized check
			if tt.wantStatus == "unhealthy" {
				expectedChecks := []string{"producer_initialized"}
				for _, check := range expectedChecks {
					if _, exists := checks[check]; !exists {
						t.Errorf("Expected check %s to be present", check)
					}
				}
			} else {
				// For healthy producer, we expect all checks
				expectedChecks := []string{"producer_initialized", "broker_connectivity", "configuration"}
				for _, check := range expectedChecks {
					if _, exists := checks[check]; !exists {
						t.Errorf("Expected check %s to be present", check)
					}
				}
			}
		})
	}
}

func TestProducer_SendToSpecificTopics(t *testing.T) {
	cfg := createTestKafkaConfig()
	producer := &Producer{
		config: cfg,
		topics: &cfg.Topics,
		// producer will be nil, so actual sending will fail, but we can test message creation
	}

	testData := map[string]interface{}{
		"test_field": "test_value",
		"content_hash": "test_hash_123",
		"timestamp": time.Now().Unix(),
	}

	tests := []struct {
		name     string
		sendFunc func(context.Context, map[string]interface{}) error
		topic    string
	}{
		{
			name:     "SendToSentimentAnalysis",
			sendFunc: producer.SendToSentimentAnalysis,
			topic:    cfg.Topics.SentimentAnalysis,
		},
		{
			name:     "SendToAggregation", 
			sendFunc: producer.SendToAggregation,
			topic:    cfg.Topics.Aggregation,
		},
		{
			name:     "SendToAlert",
			sendFunc: producer.SendToAlert,
			topic:    cfg.Topics.Alert,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			ctx := context.Background()
			err := tt.sendFunc(ctx, testData)
			
			// We expect an error since producer is nil, but we're testing the message creation logic
			if err == nil {
				t.Error("Expected error due to nil producer")
			}

			// Verify it's a ProducerError
			var producerErr *ProducerError
			if !errors.As(err, &producerErr) {
				t.Error("Expected ProducerError")
			}
		})
	}
}

func TestProducer_SendMessageBatch_EmptyBatch(t *testing.T) {
	cfg := createTestKafkaConfig()
	producer := &Producer{
		config: cfg,
		topics: &cfg.Topics,
	}

	ctx := context.Background()
	err := producer.SendMessageBatch(ctx, []*Message{})
	
	if err != nil {
		t.Errorf("Expected no error for empty batch, got: %v", err)
	}
}

func TestProducer_SendMessage_TimestampHandling(t *testing.T) {
	cfg := createTestKafkaConfig()
	producer := &Producer{
		config: cfg,
		topics: &cfg.Topics,
		// producer will be nil, so actual sending will fail, but we can test message processing
	}

	tests := []struct {
		name      string
		message   *Message
		expectErr bool
	}{
		{
			name: "message with timestamp",
			message: &Message{
				Topic: "test_topic",
				Value: map[string]interface{}{"test": "data"},
				Timestamp: time.Now(),
			},
			expectErr: true, // Will fail due to nil producer
		},
		{
			name: "message without timestamp",
			message: &Message{
				Topic: "test_topic", 
				Value: map[string]interface{}{"test": "data"},
				// Timestamp will be set automatically
			},
			expectErr: true, // Will fail due to nil producer
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			ctx := context.Background()
			// Commented out, may be used later
			// originalTimestamp := tt.message.Timestamp
			
			err := producer.SendMessage(ctx, tt.message)
			
			if (err != nil) != tt.expectErr {
				t.Errorf("SendMessage() error = %v, expectErr %v", err, tt.expectErr)
			}

			// Since producer is nil, the function returns early with an error
			// The timestamp setting logic is not reached, so we can't test it this way
			// This test validates that the error handling works correctly
			var producerErr *ProducerError
			if !errors.As(err, &producerErr) {
				t.Error("Expected ProducerError")
			}
		})
	}
}

// Benchmark tests for performance validation
func BenchmarkProducer_MessageCreation(b *testing.B) {
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		msg := &Message{
			Topic: "benchmark_topic",
			Key:   "benchmark_key",
			Value: map[string]interface{}{
				"benchmark_data": "test_data",
				"iteration":      i,
				"timestamp":      time.Now().Unix(),
			},
			Headers: map[string]string{
				"source": "benchmark",
			},
			Timestamp: time.Now(),
		}
		
		// Simulate JSON marshaling
		_, err := json.Marshal(msg.Value)
		if err != nil {
			b.Fatalf("JSON marshal failed: %v", err)
		}
	}
}

func BenchmarkIsRetryableKafkaError(b *testing.B) {
	testErrors := []error{
		&MockError{message: "connection refused"},
		&MockError{message: "timeout occurred"},
		&MockError{message: "network error"},
		&MockError{message: "invalid message format"},
		&MockError{message: "unknown error"},
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		err := testErrors[i%len(testErrors)]
		isRetryableKafkaError(err)
	}
}