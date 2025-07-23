package server

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"rtsa-ingestion/internal/config"
)

// createTestConfig creates a test configuration
func createTestConfig() *config.Config {
	return &config.Config{
		Server: config.ServerConfig{
			Port:         8080,
			Host:         "localhost",
			ReadTimeout:  30 * time.Second,
			WriteTimeout: 30 * time.Second,
			IdleTimeout:  120 * time.Second,
		},
		Database: config.DatabaseConfig{
			Host:            "localhost",
			Port:            5432,
			Name:            "test_db",
			User:            "test_user",
			Password:        "test_password",
			PoolSize:        5,
			MaxIdleConns:    2,
			MaxOpenConns:    10,
			ConnMaxLifetime: 30 * time.Minute,
		},
		Kafka: config.KafkaConfig{
			Brokers: []string{"localhost:9092"},
			Topics: config.KafkaTopicsConfig{
				SentimentAnalysis: "test_topic",
			},
		},
		RateLimit: config.RateLimitConfig{
			RequestsPerSecond: 100,
			BurstSize:         200,
			CleanupInterval:   60 * time.Second,
		},
		Logging: config.LoggingConfig{
			Level:  "INFO",
			Format: "json",
			Output: "stdout",
		},
		Health: config.HealthConfig{
			CheckInterval: 30 * time.Second,
			Timeout:       5 * time.Second,
		},
		CORS: config.CORSConfig{
			AllowedOrigins: []string{"*"},
			AllowedMethods: []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"},
			AllowedHeaders: []string{"Content-Type", "Authorization"},
		},
		Webhooks: config.WebhooksConfig{
			Timeout:     30 * time.Second,
			MaxBodySize: 10485760,
		},
	}
}

func TestNew(t *testing.T) {
	cfg := createTestConfig()

	server, err := New(cfg)
	if err != nil {
		t.Fatalf("Failed to create server: %v", err)
	}

	if server == nil {
		t.Fatal("Server is nil")
	}

	if server.config != cfg {
		t.Error("Server config not set correctly")
	}

	if server.router == nil {
		t.Error("Router not initialized")
	}
}

func TestHealthEndpoint(t *testing.T) {
	cfg := createTestConfig()
	server, err := New(cfg)
	if err != nil {
		t.Fatalf("Failed to create server: %v", err)
	}

	// Create a test request
	req, err := http.NewRequest("GET", "/health", nil)
	if err != nil {
		t.Fatalf("Failed to create request: %v", err)
	}

	// Create a response recorder
	rr := httptest.NewRecorder()

	// Perform the request
	server.router.ServeHTTP(rr, req)

	// Check status code
	if status := rr.Code; status != http.StatusOK {
		t.Errorf("Health endpoint returned wrong status code: got %v want %v", status, http.StatusOK)
	}

	// Check response body
	var response map[string]interface{}
	if err := json.Unmarshal(rr.Body.Bytes(), &response); err != nil {
		t.Fatalf("Failed to unmarshal response: %v", err)
	}

	// Verify required fields
	if response["status"] == nil {
		t.Error("Health response missing status field")
	}

	if response["timestamp"] == nil {
		t.Error("Health response missing timestamp field")
	}

	if response["checks"] == nil {
		t.Error("Health response missing checks field")
	}
}

func TestMetricsEndpoint(t *testing.T) {
	cfg := createTestConfig()
	server, err := New(cfg)
	if err != nil {
		t.Fatalf("Failed to create server: %v", err)
	}

	// Create a test request
	req, err := http.NewRequest("GET", "/metrics", nil)
	if err != nil {
		t.Fatalf("Failed to create request: %v", err)
	}

	// Create a response recorder
	rr := httptest.NewRecorder()

	// Perform the request
	server.router.ServeHTTP(rr, req)

	// Check status code
	if status := rr.Code; status != http.StatusOK {
		t.Errorf("Metrics endpoint returned wrong status code: got %v want %v", status, http.StatusOK)
	}

	// Check response body
	var response map[string]interface{}
	if err := json.Unmarshal(rr.Body.Bytes(), &response); err != nil {
		t.Fatalf("Failed to unmarshal response: %v", err)
	}

	// Verify required fields
	if response["system"] == nil {
		t.Error("Metrics response missing system field")
	}

	if response["http"] == nil {
		t.Error("Metrics response missing http field")
	}
}

func TestWebhookEndpoints(t *testing.T) {
	cfg := createTestConfig()
	server, err := New(cfg)
	if err != nil {
		t.Fatalf("Failed to create server: %v", err)
	}

	webhookEndpoints := []string{
		"/webhook/truedata",
		"/webhook/news",
		"/webhook/twitter",
		"/webhook/reddit",
		"/webhook/economic",
	}

	for _, endpoint := range webhookEndpoints {
		t.Run(endpoint, func(t *testing.T) {
			// Create a test request
			req, err := http.NewRequest("POST", endpoint, nil)
			if err != nil {
				t.Fatalf("Failed to create request: %v", err)
			}

			// Create a response recorder
			rr := httptest.NewRecorder()

			// Perform the request
			server.router.ServeHTTP(rr, req)

			// Check status code
			if status := rr.Code; status != http.StatusOK {
				t.Errorf("Webhook endpoint %s returned wrong status code: got %v want %v", endpoint, status, http.StatusOK)
			}

			// Check response body
			var response map[string]interface{}
			if err := json.Unmarshal(rr.Body.Bytes(), &response); err != nil {
				t.Fatalf("Failed to unmarshal response: %v", err)
			}

			// Verify response structure
			if response["status"] == nil {
				t.Errorf("Webhook response missing status field for %s", endpoint)
			}

			if response["message"] == nil {
				t.Errorf("Webhook response missing message field for %s", endpoint)
			}
		})
	}
}

func TestCORSMiddleware(t *testing.T) {
	cfg := createTestConfig()
	server, err := New(cfg)
	if err != nil {
		t.Fatalf("Failed to create server: %v", err)
	}

	// Create a test request with Origin header
	req, err := http.NewRequest("GET", "/health", nil)
	if err != nil {
		t.Fatalf("Failed to create request: %v", err)
	}
	req.Header.Set("Origin", "http://localhost:3000")

	// Create a response recorder
	rr := httptest.NewRecorder()

	// Perform the request
	server.router.ServeHTTP(rr, req)

	// Check CORS headers
	if rr.Header().Get("Access-Control-Allow-Origin") == "" {
		t.Error("CORS middleware not setting Access-Control-Allow-Origin header")
	}

	if rr.Header().Get("Access-Control-Allow-Methods") == "" {
		t.Error("CORS middleware not setting Access-Control-Allow-Methods header")
	}
}

func TestOptionsRequest(t *testing.T) {
	cfg := createTestConfig()
	server, err := New(cfg)
	if err != nil {
		t.Fatalf("Failed to create server: %v", err)
	}

	// Create an OPTIONS request
	req, err := http.NewRequest("OPTIONS", "/webhook/truedata", nil)
	if err != nil {
		t.Fatalf("Failed to create request: %v", err)
	}
	req.Header.Set("Origin", "http://localhost:3000")

	// Create a response recorder
	rr := httptest.NewRecorder()

	// Perform the request
	server.router.ServeHTTP(rr, req)

	// Check status code for preflight request
	if status := rr.Code; status != http.StatusNoContent {
		t.Errorf("OPTIONS request returned wrong status code: got %v want %v", status, http.StatusNoContent)
	}
}
