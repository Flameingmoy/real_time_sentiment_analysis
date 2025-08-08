package handlers

import (
	"context"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"rtsa-ingestion/internal/config"
	"rtsa-ingestion/internal/database"
	"rtsa-ingestion/internal/kafka"
)

// HealthStatus represents the health status of a component
type HealthStatus struct {
	Status    string                 `json:"status"`
	Timestamp string                 `json:"timestamp"`
	Version   string                 `json:"version"`
	Uptime    string                 `json:"uptime"`
	Checks    map[string]interface{} `json:"checks"`
}

// ComponentHealth represents the health of an individual component
type ComponentHealth struct {
	Status  string `json:"status"`
	Message string `json:"message,omitempty"`
	Latency string `json:"latency,omitempty"`
}

var startTime = time.Now()

// HealthCheck creates a health check handler
func HealthCheck(cfg *config.Config, db *database.Database, producer *kafka.Producer) gin.HandlerFunc {
	return func(c *gin.Context) {
		checks := make(map[string]interface{})
		overallStatus := "healthy"

		// Check server health
		checks["server"] = ComponentHealth{
			Status:  "healthy",
			Message: "HTTP server is running",
		}

		// Check database health
		dbStart := time.Now()
		ctx, cancel := context.WithTimeout(c.Request.Context(), 5*time.Second)
		defer cancel()
		if err := db.HealthCheck(ctx); err != nil {
			checks["database"] = ComponentHealth{
				Status:  "unhealthy",
				Message: err.Error(),
				Latency: time.Since(dbStart).String(),
			}
			overallStatus = "unhealthy"
		} else {
			checks["database"] = ComponentHealth{
				Status:  "healthy",
				Message: "Database connection is working",
				Latency: time.Since(dbStart).String(),
			}
		}

		// Check Kafka producer health
		if producer != nil {
			kafkaStart := time.Now()
			kafkaCtx, kafkaCancel := context.WithTimeout(c.Request.Context(), 5*time.Second)
			defer kafkaCancel()
			if err := producer.HealthCheck(kafkaCtx); err != nil {
				checks["kafka"] = ComponentHealth{
					Status:  "unhealthy",
					Message: err.Error(),
					Latency: time.Since(kafkaStart).String(),
				}
				overallStatus = "unhealthy"
			} else {
				checks["kafka"] = ComponentHealth{
					Status:  "healthy",
					Message: "Kafka producer is working",
					Latency: time.Since(kafkaStart).String(),
				}
			}
		} else {
			checks["kafka"] = ComponentHealth{
				Status:  "unhealthy",
				Message: "Kafka producer not initialized",
			}
			overallStatus = "unhealthy"
		}

		// Check configuration
		checks["config"] = ComponentHealth{
			Status:  "healthy",
			Message: "Configuration loaded successfully",
		}

		// Calculate uptime
		uptime := time.Since(startTime)

		response := HealthStatus{
			Status:    overallStatus,
			Timestamp: time.Now().Format(time.RFC3339),
			Version:   "1.0.0", // TODO: Get from build info
			Uptime:    uptime.String(),
			Checks:    checks,
		}

		// Return appropriate status code
		statusCode := http.StatusOK
		if overallStatus != "healthy" {
			statusCode = http.StatusServiceUnavailable
		}

		c.JSON(statusCode, response)
	}
}
