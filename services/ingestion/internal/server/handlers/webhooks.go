package handlers

import (
	"context"
	"log"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"rtsa-ingestion/internal/database"
	"rtsa-ingestion/internal/kafka"
)

// WebhookResponse represents a standard webhook response
type WebhookResponse struct {
	Status  string `json:"status"`
	Message string `json:"message"`
	ID      string `json:"id,omitempty"`
}

// processWebhookData is a helper function to process incoming webhook data
func processWebhookData(c *gin.Context, db *database.Database, producer *kafka.Producer, source string) {
	// Parse request body
	var requestData map[string]interface{}
	if err := c.ShouldBindJSON(&requestData); err != nil {
		c.JSON(http.StatusBadRequest, WebhookResponse{
			Status:  "error",
			Message: "Invalid JSON payload: " + err.Error(),
		})
		return
	}

	// Extract source ID if available
	sourceID := ""
	if id, exists := requestData["id"]; exists {
		if idStr, ok := id.(string); ok {
			sourceID = idStr
		}
	}

	// Create raw data message
	rawData := &database.RawDataMessage{
		Source:    source,
		SourceID:  sourceID,
		Content:   requestData,
		Timestamp: time.Now(),
	}

	// Insert into database with timeout
	ctx, cancel := context.WithTimeout(c.Request.Context(), 5*time.Second)
	defer cancel()

	if err := db.InsertRawData(ctx, rawData); err != nil {
		c.JSON(http.StatusInternalServerError, WebhookResponse{
			Status:  "error",
			Message: "Failed to store data: " + err.Error(),
		})
		return
	}

	// Send message to Kafka for sentiment analysis processing
	if producer != nil {
		kafkaData := map[string]interface{}{
			"source":       source,
			"source_id":    sourceID,
			"content":      requestData,
			"content_hash": rawData.ContentHash,
			"timestamp":    rawData.Timestamp.Unix(),
		}

		// Use WithRetry for robust message publishing
		err := producer.WithRetry(ctx, "send_to_sentiment_analysis", func() error {
			return producer.SendToSentimentAnalysis(ctx, kafkaData)
		})

		if err != nil {
			// Log error but don't fail the request - data is already stored
			log.Printf("Failed to send message to Kafka for source %s: %v", source, err)
		}
	}

	// Return success response
	c.JSON(http.StatusOK, WebhookResponse{
		Status:  "success",
		Message: "Data received and stored successfully",
		ID:      rawData.ContentHash,
	})
}

// TrueDataWebhook handles TrueData API webhooks
func TrueDataWebhook(db *database.Database, producer *kafka.Producer) gin.HandlerFunc {
	return func(c *gin.Context) {
		processWebhookData(c, db, producer, "truedata")
	}
}

// NewsWebhook handles news API webhooks
func NewsWebhook(db *database.Database, producer *kafka.Producer) gin.HandlerFunc {
	return func(c *gin.Context) {
		processWebhookData(c, db, producer, "news")
	}
}

// TwitterWebhook handles Twitter API webhooks
func TwitterWebhook(db *database.Database, producer *kafka.Producer) gin.HandlerFunc {
	return func(c *gin.Context) {
		processWebhookData(c, db, producer, "twitter")
	}
}

// RedditWebhook handles Reddit API webhooks
func RedditWebhook(db *database.Database, producer *kafka.Producer) gin.HandlerFunc {
	return func(c *gin.Context) {
		processWebhookData(c, db, producer, "reddit")
	}
}

// EconomicWebhook handles economic data API webhooks
func EconomicWebhook(db *database.Database, producer *kafka.Producer) gin.HandlerFunc {
	return func(c *gin.Context) {
		processWebhookData(c, db, producer, "economic")
	}
}
