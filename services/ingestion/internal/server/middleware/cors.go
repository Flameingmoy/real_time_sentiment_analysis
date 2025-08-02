package middleware

import (
	"strings"

	"github.com/gin-gonic/gin"
	"rtsa-ingestion/internal/config"
)

// CORS creates a CORS middleware
func CORS(cfg config.CORSConfig) gin.HandlerFunc {
	return func(c *gin.Context) {
		origin := c.Request.Header.Get("Origin")
		
		// Check if origin is allowed
		allowed := false
		for _, allowedOrigin := range cfg.AllowedOrigins {
			if allowedOrigin == "*" || allowedOrigin == origin {
				allowed = true
				break
			}
		}

		if allowed {
			c.Header("Access-Control-Allow-Origin", origin)
		}

		// Set allowed methods
		c.Header("Access-Control-Allow-Methods", strings.Join(cfg.AllowedMethods, ", "))

		// Set allowed headers
		c.Header("Access-Control-Allow-Headers", strings.Join(cfg.AllowedHeaders, ", "))

		// Set other CORS headers
		c.Header("Access-Control-Allow-Credentials", "true")
		c.Header("Access-Control-Max-Age", "86400") // 24 hours

		// Handle preflight requests
		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(204)
			return
		}

		c.Next()
	}
}