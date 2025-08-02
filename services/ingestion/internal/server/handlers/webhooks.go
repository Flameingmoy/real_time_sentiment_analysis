package handlers

import (
	"context"
	"encoding/json"
	"log"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"rtsa-ingestion/internal/database"
	"rtsa-ingestion/internal/kafka"
	"rtsa-ingestion/internal/models"
	"rtsa-ingestion/internal/worker"
)

// WebhookResponse represents a standard webhook response
type WebhookResponse struct {
	Status  string `json:"status"`
	Message string `json:"message"`
	ID      string `json:"id,omitempty"`
}

// processAndPublish handles data persistence and messaging within a worker.
func processAndPublish(ctx context.Context, db *database.Database, producer *kafka.Producer, source, sourceID string, data interface{}) {
	// Convert struct to map[string]interface{} via JSON marshaling to handle generic data types.
	var content map[string]interface{}
	jsonBytes, err := json.Marshal(data)
	if err != nil {
		log.Printf("ERROR: Failed to marshal data for source %s: %v", source, err)
		return
	}
	if err := json.Unmarshal(jsonBytes, &content); err != nil {
		log.Printf("ERROR: Failed to unmarshal data to map for source %s: %v", source, err)
		return
	}

	// Create raw data message
	rawData := &database.RawDataMessage{
		Source:    source,
		SourceID:  sourceID,
		Content:   content, // Use the converted map
		Timestamp: time.Now(),
	}

	// Insert into database
	if err := db.InsertRawData(ctx, rawData); err != nil {
		log.Printf("ERROR: Failed to store data for source %s: %v", source, err)
		return
	}

	// Send message to Kafka for sentiment analysis processing
	if producer != nil {
		kafkaData := map[string]interface{}{
			"source":       source,
			"source_id":    sourceID,
			"content":      content, // Use the converted map
			"content_hash": rawData.ContentHash,
			"timestamp":    rawData.Timestamp.Unix(),
		}

		err := producer.WithRetry(ctx, "send_to_sentiment_analysis", func() error {
			return producer.SendToSentimentAnalysis(ctx, kafkaData)
		})

		if err != nil {
			log.Printf("ERROR: Failed to send message to Kafka for source %s: %v", source, err)
		}
	} else {
		log.Printf("WARN: Kafka producer is nil. Skipping message sending for source %s.", source)
	}

	log.Printf("INFO: Successfully processed and published data for source %s, ID: %s", source, rawData.ContentHash)
}

// TrueDataWebhook handles TrueData API webhooks
func TrueDataWebhook(db *database.Database, producer *kafka.Producer, dispatcher *worker.Dispatcher) gin.HandlerFunc {
	return func(c *gin.Context) {
		var data models.TrueData
		if err := c.ShouldBindJSON(&data); err != nil {
			c.JSON(http.StatusBadRequest, WebhookResponse{Status: "error", Message: "Invalid payload: " + err.Error()})
			return
		}

		job := worker.Job{
			Process: func(ctx context.Context) {
				processAndPublish(ctx, db, producer, "truedata", data.ID, data)
			},
		}
		dispatcher.Submit(job)

		c.JSON(http.StatusAccepted, WebhookResponse{Status: "success", Message: "Request accepted for processing."})
	}
}

// NewsWebhook handles news API webhooks
func NewsWebhook(db *database.Database, producer *kafka.Producer, dispatcher *worker.Dispatcher) gin.HandlerFunc {
	return func(c *gin.Context) {
		var data models.NewsArticle
		if err := c.ShouldBindJSON(&data); err != nil {
			c.JSON(http.StatusBadRequest, WebhookResponse{Status: "error", Message: "Invalid payload: " + err.Error()})
			return
		}

		job := worker.Job{
			Process: func(ctx context.Context) {
				processAndPublish(ctx, db, producer, "news", data.ID, data)
			},
		}
		dispatcher.Submit(job)

		c.JSON(http.StatusAccepted, WebhookResponse{Status: "success", Message: "Request accepted for processing."})
	}
}

// TwitterWebhook handles Twitter API webhooks
func TwitterWebhook(db *database.Database, producer *kafka.Producer, dispatcher *worker.Dispatcher) gin.HandlerFunc {
	return func(c *gin.Context) {
		var data models.Tweet
		if err := c.ShouldBindJSON(&data); err != nil {
			c.JSON(http.StatusBadRequest, WebhookResponse{Status: "error", Message: "Invalid payload: " + err.Error()})
			return
		}

		job := worker.Job{
			Process: func(ctx context.Context) {
				processAndPublish(ctx, db, producer, "twitter", data.ID, data)
			},
		}
		dispatcher.Submit(job)

		c.JSON(http.StatusAccepted, WebhookResponse{Status: "success", Message: "Request accepted for processing."})
	}
}

// RedditWebhook handles Reddit API webhooks
func RedditWebhook(db *database.Database, producer *kafka.Producer, dispatcher *worker.Dispatcher) gin.HandlerFunc {
	return func(c *gin.Context) {
		var data map[string]interface{}
		if err := c.ShouldBindJSON(&data); err != nil {
			c.JSON(http.StatusBadRequest, WebhookResponse{Status: "error", Message: "Invalid payload: " + err.Error()})
			return
		}

		job := worker.Job{
			Process: func(ctx context.Context) {
				processAndPublish(ctx, db, producer, "reddit", "", data)
			},
		}
		dispatcher.Submit(job)

		c.JSON(http.StatusAccepted, WebhookResponse{Status: "success", Message: "Request accepted for processing."})
	}
}

// EconomicWebhook handles economic data API webhooks
func EconomicWebhook(db *database.Database, producer *kafka.Producer, dispatcher *worker.Dispatcher) gin.HandlerFunc {
	return func(c *gin.Context) {
		var data map[string]interface{}
		if err := c.ShouldBindJSON(&data); err != nil {
			c.JSON(http.StatusBadRequest, WebhookResponse{Status: "error", Message: "Invalid payload: " + err.Error()})
			return
		}

		job := worker.Job{
			Process: func(ctx context.Context) {
				processAndPublish(ctx, db, producer, "economic", "", data)
			},
		}
		dispatcher.Submit(job)

		c.JSON(http.StatusAccepted, WebhookResponse{Status: "success", Message: "Request accepted for processing."})
	}
}