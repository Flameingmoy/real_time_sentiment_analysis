package config

import (
	"os"
	"testing"
	"time"
)

func TestLoad(t *testing.T) {
	// Create a temporary config file
	configContent := `
server:
  port: 8080
  host: "localhost"
  read_timeout: 30s
  write_timeout: 30s
  idle_timeout: 120s

database:
  host: "localhost"
  port: 5432
  name: "test_db"
  user: "test_user"
  password: "test_password"
  pool_size: 10
  max_idle_conns: 5
  max_open_conns: 10
  conn_max_lifetime: 300s

kafka:
  brokers:
    - "localhost:9092"
  topics:
    sentiment_analysis: "test_topic"
    aggregation: "aggregation_topic"
    alert: "alert_topic"
  producer:
    retry_max: 3
    retry_backoff: 100ms
    flush_frequency: 100ms
    batch_size: 100

rate_limit:
  requests_per_second: 100
  burst_size: 200
  cleanup_interval: 60s

logging:
  level: "INFO"
  format: "json"
  output: "stdout"

health:
  check_interval: 30s
  timeout: 5s

cors:
  allowed_origins:
    - "*"
  allowed_methods:
    - "GET"
    - "POST"
  allowed_headers:
    - "Content-Type"

webhooks:
  timeout: 30s
  max_body_size: 10485760
  validation:
    enabled: true
    strict_mode: false
`

	// Write to temporary file
	tmpFile, err := os.CreateTemp("", "config_test_*.yaml")
	if err != nil {
		t.Fatalf("Failed to create temp file: %v", err)
	}
	defer os.Remove(tmpFile.Name())

	if _, err := tmpFile.WriteString(configContent); err != nil {
		t.Fatalf("Failed to write config: %v", err)
	}
	tmpFile.Close()

	// Load configuration
	cfg, err := Load(tmpFile.Name())
	if err != nil {
		t.Fatalf("Failed to load config: %v", err)
	}

	// Test server config
	if cfg.Server.Port != 8080 {
		t.Errorf("Expected port 8080, got %d", cfg.Server.Port)
	}

	if cfg.Server.Host != "localhost" {
		t.Errorf("Expected host localhost, got %s", cfg.Server.Host)
	}

	if cfg.Server.ReadTimeout != 30*time.Second {
		t.Errorf("Expected read timeout 30s, got %v", cfg.Server.ReadTimeout)
	}

	// Test database config
	if cfg.Database.Host != "localhost" {
		t.Errorf("Expected database host localhost, got %s", cfg.Database.Host)
	}

	if cfg.Database.Port != 5432 {
		t.Errorf("Expected database port 5432, got %d", cfg.Database.Port)
	}

	// Test Kafka config
	if len(cfg.Kafka.Brokers) != 1 || cfg.Kafka.Brokers[0] != "localhost:9092" {
		t.Errorf("Expected Kafka broker localhost:9092, got %v", cfg.Kafka.Brokers)
	}

	if cfg.Kafka.Topics.SentimentAnalysis != "test_topic" {
		t.Errorf("Expected sentiment analysis topic test_topic, got %s", cfg.Kafka.Topics.SentimentAnalysis)
	}

	// Test rate limit config
	if cfg.RateLimit.RequestsPerSecond != 100 {
		t.Errorf("Expected requests per second 100, got %d", cfg.RateLimit.RequestsPerSecond)
	}

	// Test CORS config
	if len(cfg.CORS.AllowedOrigins) != 1 || cfg.CORS.AllowedOrigins[0] != "*" {
		t.Errorf("Expected CORS allowed origins [*], got %v", cfg.CORS.AllowedOrigins)
	}
}

func TestValidation(t *testing.T) {
	tests := []struct {
		name        string
		config      Config
		expectError bool
	}{
		{
			name: "valid config",
			config: Config{
				Server: ServerConfig{Port: 8080},
				Database: DatabaseConfig{
					Host: "localhost",
					Port: 5432,
				},
				Kafka: KafkaConfig{
					Brokers: []string{"localhost:9092"},
				},
				RateLimit: RateLimitConfig{
					RequestsPerSecond: 100,
				},
			},
			expectError: false,
		},
		{
			name: "invalid server port",
			config: Config{
				Server: ServerConfig{Port: 0},
				Database: DatabaseConfig{
					Host: "localhost",
					Port: 5432,
				},
				Kafka: KafkaConfig{
					Brokers: []string{"localhost:9092"},
				},
				RateLimit: RateLimitConfig{
					RequestsPerSecond: 100,
				},
			},
			expectError: true,
		},
		{
			name: "missing database host",
			config: Config{
				Server: ServerConfig{Port: 8080},
				Database: DatabaseConfig{
					Host: "",
					Port: 5432,
				},
				Kafka: KafkaConfig{
					Brokers: []string{"localhost:9092"},
				},
				RateLimit: RateLimitConfig{
					RequestsPerSecond: 100,
				},
			},
			expectError: true,
		},
		{
			name: "no kafka brokers",
			config: Config{
				Server: ServerConfig{Port: 8080},
				Database: DatabaseConfig{
					Host: "localhost",
					Port: 5432,
				},
				Kafka: KafkaConfig{
					Brokers: []string{},
				},
				RateLimit: RateLimitConfig{
					RequestsPerSecond: 100,
				},
			},
			expectError: true,
		},
		{
			name: "invalid rate limit",
			config: Config{
				Server: ServerConfig{Port: 8080},
				Database: DatabaseConfig{
					Host: "localhost",
					Port: 5432,
				},
				Kafka: KafkaConfig{
					Brokers: []string{"localhost:9092"},
				},
				RateLimit: RateLimitConfig{
					RequestsPerSecond: 0,
				},
			},
			expectError: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := tt.config.validate()
			if tt.expectError && err == nil {
				t.Error("Expected validation error, got nil")
			}
			if !tt.expectError && err != nil {
				t.Errorf("Expected no validation error, got: %v", err)
			}
		})
	}
}

func TestLoadNonExistentFile(t *testing.T) {
	_, err := Load("non_existent_file.yaml")
	if err == nil {
		t.Error("Expected error when loading non-existent file, got nil")
	}
}
