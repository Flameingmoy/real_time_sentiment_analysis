package middleware

import (
	"net/http"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"rtsa-ingestion/internal/config"
)

// TokenBucket represents a token bucket for rate limiting
type TokenBucket struct {
	tokens    int
	capacity  int
	refillRate int
	lastRefill time.Time
	mutex     sync.Mutex
}

// NewTokenBucket creates a new token bucket
func NewTokenBucket(capacity, refillRate int) *TokenBucket {
	return &TokenBucket{
		tokens:     capacity,
		capacity:   capacity,
		refillRate: refillRate,
		lastRefill: time.Now(),
	}
}

// TakeToken attempts to take a token from the bucket
func (tb *TokenBucket) TakeToken() bool {
	tb.mutex.Lock()
	defer tb.mutex.Unlock()

	now := time.Now()
	elapsed := now.Sub(tb.lastRefill)
	
	// Refill tokens based on elapsed time
	tokensToAdd := int(elapsed.Seconds()) * tb.refillRate
	if tokensToAdd > 0 {
		tb.tokens += tokensToAdd
		if tb.tokens > tb.capacity {
			tb.tokens = tb.capacity
		}
		tb.lastRefill = now
	}

	// Check if we can take a token
	if tb.tokens > 0 {
		tb.tokens--
		return true
	}

	return false
}

// RateLimiter manages rate limiting for different clients
type RateLimiter struct {
	buckets map[string]*TokenBucket
	mutex   sync.RWMutex
	config  config.RateLimitConfig
}

// NewRateLimiter creates a new rate limiter
func NewRateLimiter(cfg config.RateLimitConfig) *RateLimiter {
	rl := &RateLimiter{
		buckets: make(map[string]*TokenBucket),
		config:  cfg,
	}

	// Start cleanup goroutine
	go rl.cleanup()

	return rl
}

// IsAllowed checks if a request from the given client is allowed
func (rl *RateLimiter) IsAllowed(clientID string) bool {
	rl.mutex.RLock()
	bucket, exists := rl.buckets[clientID]
	rl.mutex.RUnlock()

	if !exists {
		rl.mutex.Lock()
		// Double-check after acquiring write lock
		bucket, exists = rl.buckets[clientID]
		if !exists {
			bucket = NewTokenBucket(rl.config.BurstSize, rl.config.RequestsPerSecond)
			rl.buckets[clientID] = bucket
		}
		rl.mutex.Unlock()
	}

	return bucket.TakeToken()
}

// cleanup removes old buckets periodically
func (rl *RateLimiter) cleanup() {
	ticker := time.NewTicker(rl.config.CleanupInterval)
	defer ticker.Stop()

	for range ticker.C {
		rl.mutex.Lock()
		now := time.Now()
		for clientID, bucket := range rl.buckets {
			bucket.mutex.Lock()
			if now.Sub(bucket.lastRefill) > rl.config.CleanupInterval*2 {
				delete(rl.buckets, clientID)
			}
			bucket.mutex.Unlock()
		}
		rl.mutex.Unlock()
	}
}

var rateLimiter *RateLimiter

// RateLimit creates a rate limiting middleware
func RateLimit(cfg config.RateLimitConfig) gin.HandlerFunc {
	if rateLimiter == nil {
		rateLimiter = NewRateLimiter(cfg)
	}

	return func(c *gin.Context) {
		clientID := c.ClientIP()
		
		if !rateLimiter.IsAllowed(clientID) {
			c.JSON(http.StatusTooManyRequests, gin.H{
				"error": "Rate limit exceeded",
				"message": "Too many requests from this IP address",
				"retry_after": "60s",
			})
			c.Abort()
			return
		}

		c.Next()
	}
}