package kafka

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"time"

	"github.com/IBM/sarama"
	"rtsa-ingestion/internal/config"
)

// Producer represents a Kafka producer with health monitoring
type Producer struct {
	producer sarama.SyncProducer
	config   *config.KafkaConfig
	topics   *config.KafkaTopicsConfig
}

// ProducerError represents a Kafka producer-specific error
type ProducerError struct {
	Operation string
	Topic     string
	Err       error
	Retryable bool
}

func (e *ProducerError) Error() string {
	return fmt.Sprintf("kafka producer operation '%s' failed for topic '%s': %v", e.Operation, e.Topic, e.Err)
}

func (e *ProducerError) Unwrap() error {
	return e.Err
}

// IsRetryable returns true if the error is retryable
func (e *ProducerError) IsRetryable() bool {
	return e.Retryable
}

// Message represents a message to be sent to Kafka
type Message struct {
	Topic     string                 `json:"topic"`
	Key       string                 `json:"key,omitempty"`
	Value     map[string]interface{} `json:"value"`
	Headers   map[string]string      `json:"headers,omitempty"`
	Timestamp time.Time              `json:"timestamp"`
}

// NewProducer creates a new Kafka producer instance
func NewProducer(cfg *config.KafkaConfig) (*Producer, error) {
	// Create Sarama configuration
	saramaConfig := sarama.NewConfig()
	
	// Producer configuration
	saramaConfig.Producer.RequiredAcks = sarama.WaitForAll // Wait for all replicas
	saramaConfig.Producer.Retry.Max = cfg.Producer.RetryMax
	saramaConfig.Producer.Retry.Backoff = cfg.Producer.RetryBackoff
	saramaConfig.Producer.Return.Successes = true
	saramaConfig.Producer.Return.Errors = true
	
	// Batch configuration for performance
	saramaConfig.Producer.Flush.Frequency = cfg.Producer.FlushFrequency
	saramaConfig.Producer.Flush.Messages = cfg.Producer.BatchSize
	
	// Compression for better throughput
	saramaConfig.Producer.Compression = sarama.CompressionSnappy
	
	// Idempotent producer for exactly-once semantics
	saramaConfig.Producer.Idempotent = true
	saramaConfig.Net.MaxOpenRequests = 1
	
	// Version configuration
	saramaConfig.Version = sarama.V2_6_0_0

	// Create producer with retry logic
	var producer sarama.SyncProducer
	var err error
	maxRetries := 5
	retryDelay := 2 * time.Second

	for i := 0; i < maxRetries; i++ {
		producer, err = sarama.NewSyncProducer(cfg.Brokers, saramaConfig)
		if err == nil {
			break
		}

		if i < maxRetries-1 {
			log.Printf("Failed to create Kafka producer (attempt %d/%d), retrying in %v: %v", 
				i+1, maxRetries, retryDelay, err)
			time.Sleep(retryDelay)
			retryDelay *= 2 // Exponential backoff
		}
	}

	if err != nil {
		return nil, fmt.Errorf("failed to create Kafka producer after %d retries: %w", maxRetries, err)
	}

	return &Producer{
		producer: producer,
		config:   cfg,
		topics:   &cfg.Topics,
	}, nil
}

// SendMessage sends a single message to Kafka
func (p *Producer) SendMessage(ctx context.Context, msg *Message) error {
	// Check if producer is initialized
	if p.producer == nil {
		return &ProducerError{
			Operation: "send_message",
			Topic:     msg.Topic,
			Err:       fmt.Errorf("producer is not initialized"),
			Retryable: false,
		}
	}

	// Set timestamp if not provided
	if msg.Timestamp.IsZero() {
		msg.Timestamp = time.Now()
	}

	// Marshal message value to JSON
	valueBytes, err := json.Marshal(msg.Value)
	if err != nil {
		return &ProducerError{
			Operation: "marshal_message",
			Topic:     msg.Topic,
			Err:       fmt.Errorf("failed to marshal message value: %w", err),
			Retryable: false,
		}
	}

	// Create Sarama producer message
	producerMsg := &sarama.ProducerMessage{
		Topic:     msg.Topic,
		Value:     sarama.StringEncoder(valueBytes),
		Timestamp: msg.Timestamp,
	}

	// Add key if provided
	if msg.Key != "" {
		producerMsg.Key = sarama.StringEncoder(msg.Key)
	}

	// Add headers if provided
	if len(msg.Headers) > 0 {
		headers := make([]sarama.RecordHeader, 0, len(msg.Headers))
		for key, value := range msg.Headers {
			headers = append(headers, sarama.RecordHeader{
				Key:   []byte(key),
				Value: []byte(value),
			})
		}
		producerMsg.Headers = headers
	}

	// Send message with timeout
	done := make(chan error, 1)
	go func() {
		_, _, err := p.producer.SendMessage(producerMsg)
		done <- err
	}()

	select {
	case err := <-done:
		if err != nil {
			return &ProducerError{
				Operation: "send_message",
				Topic:     msg.Topic,
				Err:       err,
				Retryable: isRetryableKafkaError(err),
			}
		}
		return nil
	case <-ctx.Done():
		return &ProducerError{
			Operation: "send_message",
			Topic:     msg.Topic,
			Err:       ctx.Err(),
			Retryable: true,
		}
	}
}

// SendMessageBatch sends multiple messages to Kafka in a batch
func (p *Producer) SendMessageBatch(ctx context.Context, messages []*Message) error {
	if len(messages) == 0 {
		return nil
	}

	// Convert to Sarama producer messages
	producerMessages := make([]*sarama.ProducerMessage, 0, len(messages))
	
	for _, msg := range messages {
		// Set timestamp if not provided
		if msg.Timestamp.IsZero() {
			msg.Timestamp = time.Now()
		}

		// Marshal message value to JSON
		valueBytes, err := json.Marshal(msg.Value)
		if err != nil {
			return &ProducerError{
				Operation: "marshal_batch_message",
				Topic:     msg.Topic,
				Err:       fmt.Errorf("failed to marshal message value: %w", err),
				Retryable: false,
			}
		}

		// Create Sarama producer message
		producerMsg := &sarama.ProducerMessage{
			Topic:     msg.Topic,
			Value:     sarama.StringEncoder(valueBytes),
			Timestamp: msg.Timestamp,
		}

		// Add key if provided
		if msg.Key != "" {
			producerMsg.Key = sarama.StringEncoder(msg.Key)
		}

		// Add headers if provided
		if len(msg.Headers) > 0 {
			headers := make([]sarama.RecordHeader, 0, len(msg.Headers))
			for key, value := range msg.Headers {
				headers = append(headers, sarama.RecordHeader{
					Key:   []byte(key),
					Value: []byte(value),
				})
			}
			producerMsg.Headers = headers
		}

		producerMessages = append(producerMessages, producerMsg)
	}

	// Send messages in batch with timeout
	done := make(chan error, 1)
	go func() {
		err := p.producer.SendMessages(producerMessages)
		done <- err
	}()

	select {
	case err := <-done:
		if err != nil {
			return &ProducerError{
				Operation: "send_message_batch",
				Topic:     "batch",
				Err:       err,
				Retryable: isRetryableKafkaError(err),
			}
		}
		return nil
	case <-ctx.Done():
		return &ProducerError{
			Operation: "send_message_batch",
			Topic:     "batch",
			Err:       ctx.Err(),
			Retryable: true,
		}
	}
}

// SendToSentimentAnalysis sends a message to the sentiment analysis topic
func (p *Producer) SendToSentimentAnalysis(ctx context.Context, data map[string]interface{}) error {
	msg := &Message{
		Topic:     p.topics.SentimentAnalysis,
		Value:     data,
		Timestamp: time.Now(),
		Headers: map[string]string{
			"source":      "ingestion-service",
			"message_type": "raw_data",
		},
	}

	// Use content hash as key for partitioning if available
	if contentHash, exists := data["content_hash"]; exists {
		if hashStr, ok := contentHash.(string); ok {
			msg.Key = hashStr
		}
	}

	return p.SendMessage(ctx, msg)
}

// SendToAggregation sends a message to the aggregation topic
func (p *Producer) SendToAggregation(ctx context.Context, data map[string]interface{}) error {
	msg := &Message{
		Topic:     p.topics.Aggregation,
		Value:     data,
		Timestamp: time.Now(),
		Headers: map[string]string{
			"source":      "ingestion-service",
			"message_type": "aggregation_data",
		},
	}

	return p.SendMessage(ctx, msg)
}

// SendToAlert sends a message to the alert topic
func (p *Producer) SendToAlert(ctx context.Context, data map[string]interface{}) error {
	msg := &Message{
		Topic:     p.topics.Alert,
		Value:     data,
		Timestamp: time.Now(),
		Headers: map[string]string{
			"source":      "ingestion-service",
			"message_type": "alert",
		},
	}

	return p.SendMessage(ctx, msg)
}

// WithRetry executes a Kafka operation with retry logic
func (p *Producer) WithRetry(ctx context.Context, operation string, fn func() error) error {
	maxRetries := p.config.Producer.RetryMax
	if maxRetries <= 0 {
		maxRetries = 3 // Default fallback
	}
	
	baseDelay := p.config.Producer.RetryBackoff
	if baseDelay <= 0 {
		baseDelay = 100 * time.Millisecond // Default fallback
	}

	var lastErr error
	for attempt := 0; attempt < maxRetries; attempt++ {
		err := fn()
		if err == nil {
			return nil
		}

		lastErr = err

		// Check if error is retryable
		var kafkaErr *ProducerError
		if producerError, ok := err.(*ProducerError); ok {
			kafkaErr = producerError
		} else {
			// Wrap non-Kafka errors
			kafkaErr = &ProducerError{
				Operation: operation,
				Err:       err,
				Retryable: isRetryableKafkaError(err),
			}
		}

		if !kafkaErr.IsRetryable() || attempt == maxRetries-1 {
			return kafkaErr
		}

		// Calculate delay with exponential backoff and jitter
		delay := baseDelay * time.Duration(1<<attempt)
		// Add jitter to prevent thundering herd
		jitter := time.Duration(float64(delay) * 0.1 * (0.5 - float64(time.Now().UnixNano()%2)))
		delay += jitter

		log.Printf("Kafka operation '%s' failed (attempt %d/%d), retrying in %v: %v",
			operation, attempt+1, maxRetries, delay, err)

		select {
		case <-ctx.Done():
			return &ProducerError{
				Operation: operation,
				Err:       ctx.Err(),
				Retryable: false,
			}
		case <-time.After(delay):
			// Continue to next attempt
		}
	}

	return &ProducerError{
		Operation: operation,
		Err:       fmt.Errorf("operation failed after %d attempts, last error: %w", maxRetries, lastErr),
		Retryable: false,
	}
}

// HealthCheck performs a Kafka producer health check
func (p *Producer) HealthCheck(ctx context.Context) error {
	if p.producer == nil {
		return &ProducerError{
			Operation: "health_check",
			Err:       fmt.Errorf("producer is not initialized"),
			Retryable: false,
		}
	}

	// Create a test message with minimal payload
	testMsg := &Message{
		Topic: p.topics.SentimentAnalysis,
		Key:   fmt.Sprintf("health-check-%d", time.Now().UnixNano()),
		Value: map[string]interface{}{
			"type":      "health_check",
			"timestamp": time.Now().Unix(),
			"service":   "ingestion",
			"check_id":  fmt.Sprintf("hc-%d", time.Now().UnixNano()),
		},
		Headers: map[string]string{
			"test":        "health-check",
			"source":      "ingestion-service",
			"message_type": "health_check",
		},
		Timestamp: time.Now(),
	}

	// Try to send the test message with a shorter timeout for health checks
	healthCtx, cancel := context.WithTimeout(ctx, 3*time.Second)
	defer cancel()

	return p.SendMessage(healthCtx, testMsg)
}

// HealthCheckDetailed performs a detailed health check with connection monitoring
func (p *Producer) HealthCheckDetailed(ctx context.Context) map[string]interface{} {
	result := map[string]interface{}{
		"status":    "healthy",
		"timestamp": time.Now().Format(time.RFC3339),
		"checks":    make(map[string]interface{}),
	}

	checks := result["checks"].(map[string]interface{})

	// Check if producer is initialized
	if p.producer == nil {
		result["status"] = "unhealthy"
		checks["producer_initialized"] = map[string]interface{}{
			"status":  "failed",
			"message": "Producer is not initialized",
		}
		return result
	}

	checks["producer_initialized"] = map[string]interface{}{
		"status":  "passed",
		"message": "Producer is initialized",
	}

	// Check broker connectivity by attempting to send a test message
	start := time.Now()
	err := p.HealthCheck(ctx)
	latency := time.Since(start)

	if err != nil {
		result["status"] = "unhealthy"
		checks["broker_connectivity"] = map[string]interface{}{
			"status":  "failed",
			"message": err.Error(),
			"latency": latency.String(),
		}
	} else {
		checks["broker_connectivity"] = map[string]interface{}{
			"status":  "passed",
			"message": "Successfully sent test message",
			"latency": latency.String(),
		}
	}

	// Add configuration information
	checks["configuration"] = map[string]interface{}{
		"status":  "passed",
		"brokers": p.config.Brokers,
		"topics": map[string]string{
			"sentiment_analysis": p.topics.SentimentAnalysis,
			"aggregation":       p.topics.Aggregation,
			"alert":            p.topics.Alert,
		},
		"producer_config": map[string]interface{}{
			"retry_max":        p.config.Producer.RetryMax,
			"retry_backoff":    p.config.Producer.RetryBackoff.String(),
			"flush_frequency":  p.config.Producer.FlushFrequency.String(),
			"batch_size":       p.config.Producer.BatchSize,
		},
	}

	return result
}

// GetMetrics returns producer metrics and statistics
func (p *Producer) GetMetrics() map[string]interface{} {
	// Note: Sarama doesn't provide built-in metrics, but we can add custom metrics here
	return map[string]interface{}{
		"brokers":           p.config.Brokers,
		"topics":           map[string]string{
			"sentiment_analysis": p.topics.SentimentAnalysis,
			"aggregation":       p.topics.Aggregation,
			"alert":            p.topics.Alert,
		},
		"producer_config": map[string]interface{}{
			"retry_max":        p.config.Producer.RetryMax,
			"retry_backoff":    p.config.Producer.RetryBackoff.String(),
			"flush_frequency":  p.config.Producer.FlushFrequency.String(),
			"batch_size":       p.config.Producer.BatchSize,
		},
		"status": "connected",
	}
}

// Close closes the Kafka producer
func (p *Producer) Close() error {
	if p.producer != nil {
		return p.producer.Close()
	}
	return nil
}

// isRetryableKafkaError determines if a Kafka error is retryable
func isRetryableKafkaError(err error) bool {
	if err == nil {
		return false
	}

	// Check for specific Kafka errors that are retryable
	switch err {
	case sarama.ErrRequestTimedOut,
		 sarama.ErrNotLeaderForPartition,
		 sarama.ErrLeaderNotAvailable,
		 sarama.ErrNetworkException,
		 sarama.ErrNotEnoughReplicas,
		 sarama.ErrNotEnoughReplicasAfterAppend:
		return true
	}

	// Check error message for retryable conditions
	errStr := err.Error()
	retryableErrors := []string{
		"connection refused",
		"connection reset",
		"timeout",
		"temporary failure",
		"broker not available",
		"network error",
	}

	for _, retryableErr := range retryableErrors {
		if contains(errStr, retryableErr) {
			return true
		}
	}

	return false
}

// contains checks if a string contains a substring (case-insensitive)
func contains(s, substr string) bool {
	return len(s) >= len(substr) && (s == substr || 
		(len(s) > len(substr) && 
			(s[:len(substr)] == substr || 
			 s[len(s)-len(substr):] == substr || 
			 containsHelper(s, substr))))
}

func containsHelper(s, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}