package handlers

import (
	"net/http"
	"runtime"
	"time"

	"github.com/gin-gonic/gin"
	"rtsa-ingestion/internal/database"
)

// MetricsResponse represents system metrics
type MetricsResponse struct {
	Timestamp string                 `json:"timestamp"`
	System    SystemMetrics          `json:"system"`
	HTTP      HTTPMetrics            `json:"http"`
	Custom    map[string]interface{} `json:"custom"`
}

// SystemMetrics represents system-level metrics
type SystemMetrics struct {
	Uptime         string `json:"uptime"`
	GoVersion      string `json:"go_version"`
	NumGoroutines  int    `json:"num_goroutines"`
	NumCPU         int    `json:"num_cpu"`
	MemoryAlloc    uint64 `json:"memory_alloc"`
	MemoryTotal    uint64 `json:"memory_total"`
	MemorySys      uint64 `json:"memory_sys"`
	GCPauseTotal   uint64 `json:"gc_pause_total"`
	NumGC          uint32 `json:"num_gc"`
}

// HTTPMetrics represents HTTP-level metrics
type HTTPMetrics struct {
	RequestsTotal   int64 `json:"requests_total"`
	RequestsSuccess int64 `json:"requests_success"`
	RequestsError   int64 `json:"requests_error"`
	AvgResponseTime string `json:"avg_response_time"`
}

// Global metrics counters (in production, use proper metrics library like Prometheus)
var (
	requestsTotal   int64
	requestsSuccess int64
	requestsError   int64
)

// Metrics creates a metrics handler
func Metrics(db *database.Database) gin.HandlerFunc {
	return func(c *gin.Context) {
		var m runtime.MemStats
		runtime.ReadMemStats(&m)

		uptime := time.Since(startTime)

		// Get database statistics
		dbStats := db.GetStats()

		metrics := MetricsResponse{
			Timestamp: time.Now().Format(time.RFC3339),
			System: SystemMetrics{
				Uptime:         uptime.String(),
				GoVersion:      runtime.Version(),
				NumGoroutines:  runtime.NumGoroutine(),
				NumCPU:         runtime.NumCPU(),
				MemoryAlloc:    m.Alloc,
				MemoryTotal:    m.TotalAlloc,
				MemorySys:      m.Sys,
				GCPauseTotal:   m.PauseTotalNs,
				NumGC:          m.NumGC,
			},
			HTTP: HTTPMetrics{
				RequestsTotal:   requestsTotal,
				RequestsSuccess: requestsSuccess,
				RequestsError:   requestsError,
				AvgResponseTime: "0ms", // TODO: Calculate actual average
			},
			Custom: map[string]interface{}{
				"webhook_endpoints": 5,
				"rate_limit_active": true,
				"cors_enabled":      true,
				"database":          dbStats,
			},
		}

		c.JSON(http.StatusOK, metrics)
	}
}