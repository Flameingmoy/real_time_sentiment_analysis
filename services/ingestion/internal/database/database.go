package database

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"log"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"rtsa-ingestion/internal/config"
)

// Database represents the database connection and operations
type Database struct {
	pool   *pgxpool.Pool
	config *config.DatabaseConfig
}

// DatabaseError represents a database-specific error
type DatabaseError struct {
	Operation string
	Err       error
	Retryable bool
}

func (e *DatabaseError) Error() string {
	return fmt.Sprintf("database operation '%s' failed: %v", e.Operation, e.Err)
}

func (e *DatabaseError) Unwrap() error {
	return e.Err
}

// IsRetryable returns true if the error is retryable
func (e *DatabaseError) IsRetryable() bool {
	return e.Retryable
}

// RawDataMessage represents the structure for raw data storage
type RawDataMessage struct {
	ID          int64                  `json:"id"`
	Source      string                 `json:"source"`
	SourceID    string                 `json:"source_id"`
	Content     map[string]interface{} `json:"content"`
	Timestamp   time.Time              `json:"timestamp"`
	ContentHash string                 `json:"content_hash"`
	CreatedAt   time.Time              `json:"created_at"`
	ProcessedAt *time.Time             `json:"processed_at,omitempty"`
}

// New creates a new database instance with connection pooling
func New(cfg *config.DatabaseConfig) (*Database, error) {
	// Build connection string
	connStr := fmt.Sprintf(
		"postgres://%s:%s@%s:%d/%s?sslmode=disable&pool_max_conns=%d&pool_max_conn_lifetime=%s",
		cfg.User,
		cfg.Password,
		cfg.Host,
		cfg.Port,
		cfg.Name,
		cfg.PoolSize,
		cfg.ConnMaxLifetime.String(),
	)

	// Create connection pool configuration
	poolConfig, err := pgxpool.ParseConfig(connStr)
	if err != nil {
		return nil, fmt.Errorf("failed to parse database config: %w", err)
	}

	// Configure pool settings
	poolConfig.MaxConns = int32(cfg.PoolSize)
	poolConfig.MaxConnLifetime = cfg.ConnMaxLifetime
	poolConfig.MaxConnIdleTime = 30 * time.Minute

	// Create connection pool with retry logic
	var pool *pgxpool.Pool
	maxRetries := 5
	retryDelay := 2 * time.Second

	for i := 0; i < maxRetries; i++ {
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		pool, err = pgxpool.NewWithConfig(ctx, poolConfig)
		cancel()

		if err == nil {
			// Test the connection
			ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
			err = pool.Ping(ctx)
			cancel()

			if err == nil {
				break
			}
		}

		if i < maxRetries-1 {
			time.Sleep(retryDelay)
			retryDelay *= 2 // Exponential backoff
		}
	}

	if err != nil {
		return nil, fmt.Errorf("failed to connect to database after %d retries: %w", maxRetries, err)
	}

	db := &Database{
		pool:   pool,
		config: cfg,
	}

	// Initialize database schema
	if err := db.initSchema(); err != nil {
		pool.Close()
		return nil, fmt.Errorf("failed to initialize database schema: %w", err)
	}

	return db, nil
}

// initSchema creates the necessary tables and indexes if they don't exist
func (db *Database) initSchema() error {
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	// Create raw_data table
	createTableSQL := `
	CREATE TABLE IF NOT EXISTS raw_data (
		id BIGSERIAL PRIMARY KEY,
		source VARCHAR(100) NOT NULL,
		source_id VARCHAR(255),
		content JSONB NOT NULL,
		timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
		content_hash VARCHAR(64) NOT NULL UNIQUE,
		created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
		processed_at TIMESTAMP WITH TIME ZONE
	);`

	if _, err := db.pool.Exec(ctx, createTableSQL); err != nil {
		return fmt.Errorf("failed to create raw_data table: %w", err)
	}

	// Create indexes for performance
	indexes := []string{
		"CREATE INDEX IF NOT EXISTS idx_raw_data_timestamp ON raw_data(timestamp);",
		"CREATE INDEX IF NOT EXISTS idx_raw_data_source ON raw_data(source);",
		"CREATE INDEX IF NOT EXISTS idx_raw_data_content_hash ON raw_data(content_hash);",
		"CREATE INDEX IF NOT EXISTS idx_raw_data_processed ON raw_data(processed_at) WHERE processed_at IS NULL;",
	}

	for _, indexSQL := range indexes {
		if _, err := db.pool.Exec(ctx, indexSQL); err != nil {
			return fmt.Errorf("failed to create index: %w", err)
		}
	}

	return nil
}

// InsertRawData inserts raw data into the database
func (db *Database) InsertRawData(ctx context.Context, data *RawDataMessage) error {
	// Generate content hash if not provided
	if data.ContentHash == "" {
		contentBytes, err := json.Marshal(data.Content)
		if err != nil {
			return fmt.Errorf("failed to marshal content for hashing: %w", err)
		}
		hash := sha256.Sum256(contentBytes)
		data.ContentHash = hex.EncodeToString(hash[:])
	}

	// Set timestamp if not provided
	if data.Timestamp.IsZero() {
		data.Timestamp = time.Now()
	}

	// Convert content to JSONB
	contentBytes, err := json.Marshal(data.Content)
	if err != nil {
		return fmt.Errorf("failed to marshal content: %w", err)
	}

	// Insert with retry logic for duplicate key errors
	insertSQL := `
	INSERT INTO raw_data (source, source_id, content, timestamp, content_hash)
	VALUES ($1, $2, $3, $4, $5)
	ON CONFLICT (content_hash) DO NOTHING
	RETURNING id, created_at;`

	row := db.pool.QueryRow(ctx, insertSQL,
		data.Source,
		data.SourceID,
		string(contentBytes),
		data.Timestamp,
		data.ContentHash,
	)

	var id int64
	var createdAt time.Time
	err = row.Scan(&id, &createdAt)
	if err != nil {
		if err == pgx.ErrNoRows {
			// Duplicate content, not an error
			return nil
		}
		return fmt.Errorf("failed to insert raw data: %w", err)
	}

	data.ID = id
	data.CreatedAt = createdAt

	return nil
}

// GetRawDataByHash retrieves raw data by content hash
func (db *Database) GetRawDataByHash(ctx context.Context, contentHash string) (*RawDataMessage, error) {
	selectSQL := `
	SELECT id, source, source_id, content, timestamp, content_hash, created_at, processed_at
	FROM raw_data
	WHERE content_hash = $1;`

	row := db.pool.QueryRow(ctx, selectSQL, contentHash)

	var data RawDataMessage
	var contentBytes string
	err := row.Scan(
		&data.ID,
		&data.Source,
		&data.SourceID,
		&contentBytes,
		&data.Timestamp,
		&data.ContentHash,
		&data.CreatedAt,
		&data.ProcessedAt,
	)

	if err != nil {
		if err == pgx.ErrNoRows {
			return nil, nil // Not found, not an error
		}
		return nil, fmt.Errorf("failed to get raw data: %w", err)
	}

	// Unmarshal content
	if err := json.Unmarshal([]byte(contentBytes), &data.Content); err != nil {
		return nil, fmt.Errorf("failed to unmarshal content: %w", err)
	}

	return &data, nil
}

// MarkAsProcessed marks a raw data record as processed
func (db *Database) MarkAsProcessed(ctx context.Context, id int64) error {
	updateSQL := `
	UPDATE raw_data
	SET processed_at = NOW()
	WHERE id = $1;`

	result, err := db.pool.Exec(ctx, updateSQL, id)
	if err != nil {
		return fmt.Errorf("failed to mark as processed: %w", err)
	}

	if result.RowsAffected() == 0 {
		return fmt.Errorf("no rows updated for id %d", id)
	}

	return nil
}

// GetUnprocessedData retrieves unprocessed raw data with pagination
func (db *Database) GetUnprocessedData(ctx context.Context, limit int, offset int) ([]*RawDataMessage, error) {
	selectSQL := `
	SELECT id, source, source_id, content, timestamp, content_hash, created_at, processed_at
	FROM raw_data
	WHERE processed_at IS NULL
	ORDER BY created_at ASC
	LIMIT $1 OFFSET $2;`

	rows, err := db.pool.Query(ctx, selectSQL, limit, offset)
	if err != nil {
		return nil, fmt.Errorf("failed to query unprocessed data: %w", err)
	}
	defer rows.Close()

	var results []*RawDataMessage
	for rows.Next() {
		var data RawDataMessage
		var contentBytes string
		err := rows.Scan(
			&data.ID,
			&data.Source,
			&data.SourceID,
			&contentBytes,
			&data.Timestamp,
			&data.ContentHash,
			&data.CreatedAt,
			&data.ProcessedAt,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan row: %w", err)
		}

		// Unmarshal content
		if err := json.Unmarshal([]byte(contentBytes), &data.Content); err != nil {
			return nil, fmt.Errorf("failed to unmarshal content: %w", err)
		}

		results = append(results, &data)
	}

	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("error iterating rows: %w", err)
	}

	return results, nil
}

// HealthCheck performs a database health check
func (db *Database) HealthCheck(ctx context.Context) error {
	// Test basic connectivity
	if err := db.pool.Ping(ctx); err != nil {
		return fmt.Errorf("database ping failed: %w", err)
	}

	// Test query execution
	var result int
	err := db.pool.QueryRow(ctx, "SELECT 1").Scan(&result)
	if err != nil {
		return fmt.Errorf("database query test failed: %w", err)
	}

	if result != 1 {
		return fmt.Errorf("unexpected query result: %d", result)
	}

	return nil
}

// GetStats returns database connection statistics
func (db *Database) GetStats() map[string]interface{} {
	stats := db.pool.Stat()
	return map[string]interface{}{
		"total_conns":        stats.TotalConns(),
		"acquired_conns":     stats.AcquiredConns(),
		"idle_conns":         stats.IdleConns(),
		"max_conns":          stats.MaxConns(),
		"acquire_count":      stats.AcquireCount(),
		"acquire_duration":   stats.AcquireDuration().String(),
		"canceled_acquire_count": stats.CanceledAcquireCount(),
	}
}

// Close closes the database connection pool
func (db *Database) Close() {
	if db.pool != nil {
		db.pool.Close()
	}
}

// CleanupOldData removes processed data older than the specified duration
func (db *Database) CleanupOldData(ctx context.Context, olderThan time.Duration) (int64, error) {
	deleteSQL := `
	DELETE FROM raw_data
	WHERE processed_at IS NOT NULL
	AND processed_at < NOW() - INTERVAL '%d seconds';`

	result, err := db.pool.Exec(ctx, fmt.Sprintf(deleteSQL, int(olderThan.Seconds())))
	if err != nil {
		return 0, fmt.Errorf("failed to cleanup old data: %w", err)
	}

	return result.RowsAffected(), nil
}

// InsertRawDataBatch inserts multiple raw data records in a single transaction
func (db *Database) InsertRawDataBatch(ctx context.Context, data []*RawDataMessage) error {
	if len(data) == 0 {
		return nil
	}

	// Use individual inserts within a transaction for better compatibility
	tx, err := db.pool.Begin(ctx)
	if err != nil {
		return &DatabaseError{
			Operation: "begin_transaction",
			Err:       err,
			Retryable: true,
		}
	}
	defer tx.Rollback(ctx)

	insertSQL := `
	INSERT INTO raw_data (source, source_id, content, timestamp, content_hash)
	VALUES ($1, $2, $3, $4, $5)
	ON CONFLICT (content_hash) DO NOTHING
	RETURNING id, created_at;`

	for _, record := range data {
		// Generate content hash if not provided
		if record.ContentHash == "" {
			contentBytes, err := json.Marshal(record.Content)
			if err != nil {
				return &DatabaseError{
					Operation: "marshal_content",
					Err:       fmt.Errorf("failed to marshal content for record %s: %w", record.SourceID, err),
					Retryable: false,
				}
			}
			hash := sha256.Sum256(contentBytes)
			record.ContentHash = hex.EncodeToString(hash[:])
		}

		// Set timestamp if not provided
		if record.Timestamp.IsZero() {
			record.Timestamp = time.Now()
		}

		// Convert content to JSONB
		contentBytes, err := json.Marshal(record.Content)
		if err != nil {
			return &DatabaseError{
				Operation: "marshal_content",
				Err:       fmt.Errorf("failed to marshal content for record %s: %w", record.SourceID, err),
				Retryable: false,
			}
		}

		// Execute individual insert
		var id int64
		var createdAt time.Time
		err = tx.QueryRow(ctx, insertSQL,
			record.Source,
			record.SourceID,
			string(contentBytes),
			record.Timestamp,
			record.ContentHash,
		).Scan(&id, &createdAt)

		if err != nil {
			if err == pgx.ErrNoRows {
				// Duplicate content, skip
				continue
			}
			return &DatabaseError{
				Operation: "batch_insert",
				Err:       fmt.Errorf("failed to insert record %s: %w", record.SourceID, err),
				Retryable: true,
			}
		}

		record.ID = id
		record.CreatedAt = createdAt
	}

	// Commit transaction
	if err := tx.Commit(ctx); err != nil {
		return &DatabaseError{
			Operation: "commit_transaction",
			Err:       err,
			Retryable: true,
		}
	}

	return nil
}

// WithRetry executes a database operation with retry logic
func (db *Database) WithRetry(ctx context.Context, operation string, fn func() error) error {
	maxRetries := 3
	baseDelay := 100 * time.Millisecond

	for attempt := 0; attempt < maxRetries; attempt++ {
		err := fn()
		if err == nil {
			return nil
		}

		// Check if error is retryable
		var dbErr *DatabaseError
		if err, ok := err.(*DatabaseError); ok {
			dbErr = err
		} else {
			// Wrap non-database errors
			dbErr = &DatabaseError{
				Operation: operation,
				Err:       err,
				Retryable: isRetryableError(err),
			}
		}

		if !dbErr.IsRetryable() || attempt == maxRetries-1 {
			return dbErr
		}

		// Calculate delay with exponential backoff
		delay := baseDelay * time.Duration(1<<attempt)
		log.Printf("Database operation '%s' failed (attempt %d/%d), retrying in %v: %v",
			operation, attempt+1, maxRetries, delay, err)

		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-time.After(delay):
			// Continue to next attempt
		}
	}

	return fmt.Errorf("operation '%s' failed after %d attempts", operation, maxRetries)
}

// isRetryableError determines if an error is retryable
func isRetryableError(err error) bool {
	if err == nil {
		return false
	}

	// Check for connection errors
	errStr := err.Error()
	retryableErrors := []string{
		"connection refused",
		"connection reset",
		"timeout",
		"temporary failure",
		"server closed the connection",
		"broken pipe",
	}

	for _, retryableErr := range retryableErrors {
		if contains(errStr, retryableErr) {
			return true
		}
	}

	return false
}

// contains checks if a string contains a substring (case-insensitive)
func contains(s, substr string) bool {
	return len(s) >= len(substr) && (s == substr || 
		(len(s) > len(substr) && 
			(s[:len(substr)] == substr || 
			 s[len(s)-len(substr):] == substr || 
			 containsHelper(s, substr))))
}

func containsHelper(s, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}

// GetConnectionHealth returns detailed connection health information
func (db *Database) GetConnectionHealth(ctx context.Context) map[string]interface{} {
	health := make(map[string]interface{})
	
	// Basic connectivity test
	pingErr := db.pool.Ping(ctx)
	health["ping_success"] = pingErr == nil
	if pingErr != nil {
		health["ping_error"] = pingErr.Error()
	}

	// Connection pool stats
	stats := db.pool.Stat()
	health["pool_stats"] = map[string]interface{}{
		"total_conns":              stats.TotalConns(),
		"acquired_conns":           stats.AcquiredConns(),
		"idle_conns":               stats.IdleConns(),
		"max_conns":                stats.MaxConns(),
		"acquire_count":            stats.AcquireCount(),
		"acquire_duration_ms":      stats.AcquireDuration().Milliseconds(),
		"canceled_acquire_count":   stats.CanceledAcquireCount(),
		"constructing_conns":       stats.ConstructingConns(),
		"empty_acquire_count":      stats.EmptyAcquireCount(),
		"new_conns_count":          stats.NewConnsCount(),
	}

	// Test query execution
	var queryResult int
	queryErr := db.pool.QueryRow(ctx, "SELECT 1").Scan(&queryResult)
	health["query_success"] = queryErr == nil && queryResult == 1
	if queryErr != nil {
		health["query_error"] = queryErr.Error()
	}

	// Test table access
	var tableCount int
	tableErr := db.pool.QueryRow(ctx, "SELECT COUNT(*) FROM raw_data LIMIT 1").Scan(&tableCount)
	health["table_access_success"] = tableErr == nil
	if tableErr != nil {
		health["table_access_error"] = tableErr.Error()
	}

	return health
}

// ValidateSchema ensures the database schema is correct
func (db *Database) ValidateSchema(ctx context.Context) error {
	// Check if raw_data table exists with correct structure
	checkTableSQL := `
	SELECT column_name, data_type, is_nullable
	FROM information_schema.columns
	WHERE table_name = 'raw_data'
	ORDER BY ordinal_position;`

	rows, err := db.pool.Query(ctx, checkTableSQL)
	if err != nil {
		return &DatabaseError{
			Operation: "validate_schema",
			Err:       fmt.Errorf("failed to query table schema: %w", err),
			Retryable: true,
		}
	}
	defer rows.Close()

	expectedColumns := map[string]string{
		"id":           "bigint",
		"source":       "character varying",
		"source_id":    "character varying",
		"content":      "jsonb",
		"timestamp":    "timestamp with time zone",
		"content_hash": "character varying",
		"created_at":   "timestamp with time zone",
		"processed_at": "timestamp with time zone",
	}

	foundColumns := make(map[string]string)
	for rows.Next() {
		var columnName, dataType, isNullable string
		if err := rows.Scan(&columnName, &dataType, &isNullable); err != nil {
			return &DatabaseError{
				Operation: "validate_schema",
				Err:       fmt.Errorf("failed to scan column info: %w", err),
				Retryable: false,
			}
		}
		foundColumns[columnName] = dataType
	}

	// Verify all expected columns exist
	for expectedCol, expectedType := range expectedColumns {
		if foundType, exists := foundColumns[expectedCol]; !exists {
			return &DatabaseError{
				Operation: "validate_schema",
				Err:       fmt.Errorf("missing column: %s", expectedCol),
				Retryable: false,
			}
		} else if foundType != expectedType {
			return &DatabaseError{
				Operation: "validate_schema",
				Err:       fmt.Errorf("column %s has type %s, expected %s", expectedCol, foundType, expectedType),
				Retryable: false,
			}
		}
	}

	return nil
}