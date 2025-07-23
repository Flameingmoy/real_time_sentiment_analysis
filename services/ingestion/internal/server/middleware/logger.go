package middleware

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
	"time"

	"github.com/gin-gonic/gin"
	"rtsa-ingestion/internal/config"
)

// LogEntry represents a structured log entry
type LogEntry struct {
	Timestamp    string `json:"timestamp"`
	Level        string `json:"level"`
	Component    string `json:"component"`
	Method       string `json:"method"`
	Path         string `json:"path"`
	StatusCode   int    `json:"status_code"`
	Duration     string `json:"duration"`
	ClientIP     string `json:"client_ip"`
	UserAgent    string `json:"user_agent"`
	RequestSize  int64  `json:"request_size"`
	ResponseSize int    `json:"response_size"`
	Error        string `json:"error,omitempty"`
}

// Logger creates a structured logging middleware
func Logger(cfg config.LoggingConfig) gin.HandlerFunc {
	return gin.LoggerWithFormatter(func(param gin.LogFormatterParams) string {
		entry := LogEntry{
			Timestamp:    param.TimeStamp.Format(time.RFC3339),
			Level:        "INFO",
			Component:    "http_server",
			Method:       param.Method,
			Path:         param.Path,
			StatusCode:   param.StatusCode,
			Duration:     param.Latency.String(),
			ClientIP:     param.ClientIP,
			UserAgent:    param.Request.UserAgent(),
			RequestSize:  param.Request.ContentLength,
			ResponseSize: param.BodySize,
		}

		// Add error information if present
		if param.ErrorMessage != "" {
			entry.Error = param.ErrorMessage
			entry.Level = "ERROR"
		}

		// Format based on configuration
		if cfg.Format == "json" {
			jsonData, err := json.Marshal(entry)
			if err != nil {
				log.Printf("Failed to marshal log entry: %v", err)
				return fmt.Sprintf("%s [%s] %s %s %d %s\n",
					entry.Timestamp, entry.Level, entry.Method, entry.Path, entry.StatusCode, entry.Duration)
			}
			return string(jsonData) + "\n"
		}

		// Plain text format
		return fmt.Sprintf("%s [%s] %s %s %d %s %s\n",
			entry.Timestamp, entry.Level, entry.Method, entry.Path, entry.StatusCode, entry.Duration, entry.ClientIP)
	})
}

// LogError logs an error with structured format
func LogError(component, message string, err error) {
	entry := LogEntry{
		Timestamp: time.Now().Format(time.RFC3339),
		Level:     "ERROR",
		Component: component,
		Error:     fmt.Sprintf("%s: %v", message, err),
	}

	jsonData, jsonErr := json.Marshal(entry)
	if jsonErr != nil {
		log.Printf("Failed to marshal error log: %v", jsonErr)
		log.Printf("[ERROR] %s: %s: %v", component, message, err)
		return
	}

	fmt.Fprintln(os.Stderr, string(jsonData))
}

// LogInfo logs an info message with structured format
func LogInfo(component, message string) {
	entry := LogEntry{
		Timestamp: time.Now().Format(time.RFC3339),
		Level:     "INFO",
		Component: component,
	}

	jsonData, err := json.Marshal(map[string]interface{}{
		"timestamp": entry.Timestamp,
		"level":     entry.Level,
		"component": entry.Component,
		"message":   message,
	})
	if err != nil {
		log.Printf("Failed to marshal info log: %v", err)
		log.Printf("[INFO] %s: %s", component, message)
		return
	}

	fmt.Println(string(jsonData))
}
