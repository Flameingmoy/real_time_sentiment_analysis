package config

import (
	"fmt"
	"os"
	"time"

	"gopkg.in/yaml.v3"
)

// Config represents the application configuration
type Config struct {
	Server    ServerConfig    `yaml:"server"`
	Database  DatabaseConfig  `yaml:"database"`
	Kafka     KafkaConfig     `yaml:"kafka"`
	RateLimit RateLimitConfig `yaml:"rate_limit"`
	Logging   LoggingConfig   `yaml:"logging"`
	Health    HealthConfig    `yaml:"health"`
	CORS      CORSConfig      `yaml:"cors"`
	Webhooks  WebhooksConfig  `yaml:"webhooks"`
}

// ServerConfig holds server configuration
type ServerConfig struct {
	Port         int           `yaml:"port"`
	Host         string        `yaml:"host"`
	ReadTimeout  time.Duration `yaml:"read_timeout"`
	WriteTimeout time.Duration `yaml:"write_timeout"`
	IdleTimeout  time.Duration `yaml:"idle_timeout"`
	WorkerCount  int           `yaml:"worker_count"`
	JobQueueSize int           `yaml:"job_queue_size"`
}

// DatabaseConfig holds database configuration
type DatabaseConfig struct {
	Host            string        `yaml:"host"`
	Port            int           `yaml:"port"`
	Name            string        `yaml:"name"`
	User            string        `yaml:"user"`
	Password        string        `yaml:"password"`
	PoolSize        int           `yaml:"pool_size"`
	MaxIdleConns    int           `yaml:"max_idle_conns"`
	MaxOpenConns    int           `yaml:"max_open_conns"`
	ConnMaxLifetime time.Duration `yaml:"conn_max_lifetime"`
}

// KafkaConfig holds Kafka configuration
type KafkaConfig struct {
	Brokers  []string           `yaml:"brokers"`
	Topics   KafkaTopicsConfig  `yaml:"topics"`
	Producer KafkaProducerConfig `yaml:"producer"`
}

// KafkaTopicsConfig holds Kafka topics configuration
type KafkaTopicsConfig struct {
	SentimentAnalysis string `yaml:"sentiment_analysis"`
	Aggregation       string `yaml:"aggregation"`
	Alert             string `yaml:"alert"`
}

// KafkaProducerConfig holds Kafka producer configuration
type KafkaProducerConfig struct {
	RetryMax       int           `yaml:"retry_max"`
	RetryBackoff   time.Duration `yaml:"retry_backoff"`
	FlushFrequency time.Duration `yaml:"flush_frequency"`
	BatchSize      int           `yaml:"batch_size"`
}

// RateLimitConfig holds rate limiting configuration
type RateLimitConfig struct {
	RequestsPerSecond int           `yaml:"requests_per_second"`
	BurstSize         int           `yaml:"burst_size"`
	CleanupInterval   time.Duration `yaml:"cleanup_interval"`
}

// LoggingConfig holds logging configuration
type LoggingConfig struct {
	Level  string `yaml:"level"`
	Format string `yaml:"format"`
	Output string `yaml:"output"`
}

// HealthConfig holds health check configuration
type HealthConfig struct {
	CheckInterval time.Duration `yaml:"check_interval"`
	Timeout       time.Duration `yaml:"timeout"`
}

// CORSConfig holds CORS configuration
type CORSConfig struct {
	AllowedOrigins []string `yaml:"allowed_origins"`
	AllowedMethods []string `yaml:"allowed_methods"`
	AllowedHeaders []string `yaml:"allowed_headers"`
}

// WebhooksConfig holds webhook configuration
type WebhooksConfig struct {
	Timeout     time.Duration      `yaml:"timeout"`
	MaxBodySize int64              `yaml:"max_body_size"`
	Validation  ValidationConfig   `yaml:"validation"`
}

// ValidationConfig holds validation configuration
type ValidationConfig struct {
	Enabled    bool `yaml:"enabled"`
	StrictMode bool `yaml:"strict_mode"`
}

// Load loads configuration from file
func Load(filename string) (*Config, error) {
	data, err := os.ReadFile(filename)
	if err != nil {
		return nil, fmt.Errorf("failed to read config file: %w", err)
	}

	var config Config
	if err := yaml.Unmarshal(data, &config); err != nil {
		return nil, fmt.Errorf("failed to unmarshal config: %w", err)
	}

	// Validate configuration
	if err := config.validate(); err != nil {
		return nil, fmt.Errorf("invalid configuration: %w", err)
	}

	return &config, nil
}

// validate validates the configuration
func (c *Config) validate() error {
	if c.Server.Port <= 0 || c.Server.Port > 65535 {
		return fmt.Errorf("invalid server port: %d", c.Server.Port)
	}

	if c.Database.Host == "" {
		return fmt.Errorf("database host is required")
	}

	if c.Database.Port <= 0 || c.Database.Port > 65535 {
		return fmt.Errorf("invalid database port: %d", c.Database.Port)
	}

	if len(c.Kafka.Brokers) == 0 {
		return fmt.Errorf("at least one Kafka broker is required")
	}

	if c.RateLimit.RequestsPerSecond <= 0 {
		return fmt.Errorf("requests per second must be positive")
	}

	return nil
}