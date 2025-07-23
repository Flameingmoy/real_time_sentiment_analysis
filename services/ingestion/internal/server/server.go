package server

import (
	"context"
	"fmt"
	"net/http"

	"github.com/gin-gonic/gin"
	"rtsa-ingestion/internal/config"
	"rtsa-ingestion/internal/database"
	"rtsa-ingestion/internal/kafka"
	"rtsa-ingestion/internal/server/handlers"
	"rtsa-ingestion/internal/server/middleware"
)

// Server represents the HTTP server
type Server struct {
	config     *config.Config
	router     *gin.Engine
	httpServer *http.Server
	database   *database.Database
	producer   *kafka.Producer
}

// New creates a new server instance
func New(cfg *config.Config) (*Server, error) {
	// Set Gin mode based on logging level
	if cfg.Logging.Level == "DEBUG" {
		gin.SetMode(gin.DebugMode)
	} else {
		gin.SetMode(gin.ReleaseMode)
	}

	// Initialize database connection
	db, err := database.New(&cfg.Database)
	if err != nil {
		return nil, fmt.Errorf("failed to initialize database: %w", err)
	}

	// Initialize Kafka producer
	producer, err := kafka.NewProducer(&cfg.Kafka)
	if err != nil {
		return nil, fmt.Errorf("failed to initialize Kafka producer: %w", err)
	}

	// Create Gin router
	router := gin.New()

	// Create server instance
	server := &Server{
		config:   cfg,
		router:   router,
		database: db,
		producer: producer,
	}

	// Setup middleware
	server.setupMiddleware()

	// Setup routes
	server.setupRoutes()

	return server, nil
}

// setupMiddleware configures middleware for the server
func (s *Server) setupMiddleware() {
	// Recovery middleware
	s.router.Use(gin.Recovery())

	// Custom logging middleware
	s.router.Use(middleware.Logger(s.config.Logging))

	// CORS middleware
	s.router.Use(middleware.CORS(s.config.CORS))

	// Rate limiting middleware
	s.router.Use(middleware.RateLimit(s.config.RateLimit))

	// Error handling middleware
	s.router.Use(middleware.ErrorHandler())
}

// setupRoutes configures routes for the server
func (s *Server) setupRoutes() {
	// Health check endpoint
	s.router.GET("/health", handlers.HealthCheck(s.config, s.database, s.producer))

	// Metrics endpoint
	s.router.GET("/metrics", handlers.Metrics(s.database))

	// Webhook endpoints group
	webhooks := s.router.Group("/webhook")
	{
		webhooks.POST("/truedata", handlers.TrueDataWebhook(s.database, s.producer))
		webhooks.POST("/news", handlers.NewsWebhook(s.database, s.producer))
		webhooks.POST("/twitter", handlers.TwitterWebhook(s.database, s.producer))
		webhooks.POST("/reddit", handlers.RedditWebhook(s.database, s.producer))
		webhooks.POST("/economic", handlers.EconomicWebhook(s.database, s.producer))
	}
}

// Start starts the HTTP server
func (s *Server) Start(addr string) error {
	s.httpServer = &http.Server{
		Addr:         addr,
		Handler:      s.router,
		ReadTimeout:  s.config.Server.ReadTimeout,
		WriteTimeout: s.config.Server.WriteTimeout,
		IdleTimeout:  s.config.Server.IdleTimeout,
	}

	return s.httpServer.ListenAndServe()
}

// Shutdown gracefully shuts down the server
func (s *Server) Shutdown(ctx context.Context) error {
	// Close Kafka producer
	if s.producer != nil {
		s.producer.Close()
	}

	// Close database connection
	if s.database != nil {
		s.database.Close()
	}

	// Shutdown HTTP server
	if s.httpServer == nil {
		return nil
	}
	return s.httpServer.Shutdown(ctx)
}

// GetRouter returns the Gin router (useful for testing)
func (s *Server) GetRouter() *gin.Engine {
	return s.router
}
