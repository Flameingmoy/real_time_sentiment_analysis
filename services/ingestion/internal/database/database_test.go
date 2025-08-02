package database

import (
	"context"
	"fmt"
	"testing"
	"time"

	"github.com/testcontainers/testcontainers-go"
	"github.com/testcontainers/testcontainers-go/modules/postgres"
	"github.com/testcontainers/testcontainers-go/wait"
	"rtsa-ingestion/internal/config"
)

// TestDatabase represents a test database instance
type TestDatabase struct {
	*Database
	container testcontainers.Container
}

// setupTestDatabase creates a test database instance using testcontainers
func setupTestDatabase(t *testing.T) *TestDatabase {
	t.Helper()

	ctx := context.Background()

	// Create PostgreSQL container
	postgresContainer, err := postgres.Run(ctx,
		"postgres:15-alpine",
		postgres.WithDatabase("test_rtsa_ingestion"),
		postgres.WithUsername("test_user"),
		postgres.WithPassword("test_password"),
		testcontainers.WithWaitStrategy(
			wait.ForLog("database system is ready to accept connections").
				WithOccurrence(2).
				WithStartupTimeout(30*time.Second)),
	)
	if err != nil {
		t.Skipf("Could not start postgres container: %v", err)
	}

	// Get connection details
	host, err := postgresContainer.Host(ctx)
	if err != nil {
		postgresContainer.Terminate(ctx)
		t.Fatalf("Failed to get container host: %v", err)
	}

	port, err := postgresContainer.MappedPort(ctx, "5432")
	if err != nil {
		postgresContainer.Terminate(ctx)
		t.Fatalf("Failed to get container port: %v", err)
	}

	// Create database config
	cfg := &config.DatabaseConfig{
		Host:            host,
		Port:            port.Int(),
		Name:            "test_rtsa_ingestion",
		User:            "test_user",
		Password:        "test_password",
		PoolSize:        5,
		MaxIdleConns:    2,
		MaxOpenConns:    10,
		ConnMaxLifetime: 30 * time.Minute,
	}

	// Create database instance
	db, err := New(cfg)
	if err != nil {
		postgresContainer.Terminate(ctx)
		t.Fatalf("Failed to create database instance: %v", err)
	}

	return &TestDatabase{
		Database:  db,
		container: postgresContainer,
	}
}

// teardownTestDatabase cleans up the test database
func (tdb *TestDatabase) teardownTestDatabase(t *testing.T) {
	t.Helper()
	ctx := context.Background()
	
	if tdb.Database != nil {
		tdb.Database.Close()
	}
	
	if tdb.container != nil {
		if err := tdb.container.Terminate(ctx); err != nil {
			t.Logf("Failed to terminate container: %v", err)
		}
	}
}

func TestNew(t *testing.T) {
	tests := []struct {
		name    string
		config  *config.DatabaseConfig
		wantErr bool
	}{
		{
			name: "valid config",
			config: &config.DatabaseConfig{
				Host:            "localhost",
				Port:            5432,
				Name:            "test_db",
				User:            "test_user",
				Password:        "test_password",
				PoolSize:        5,
				ConnMaxLifetime: 30 * time.Minute,
			},
			wantErr: true, // Will fail without actual database
		},
		{
			name: "invalid port",
			config: &config.DatabaseConfig{
				Host:            "localhost",
				Port:            0,
				Name:            "test_db",
				User:            "test_user",
				Password:        "test_password",
				PoolSize:        5,
				ConnMaxLifetime: 30 * time.Minute,
			},
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			db, err := New(tt.config)
			if (err != nil) != tt.wantErr {
				t.Errorf("New() error = %v, wantErr %v", err, tt.wantErr)
				return
			}
			if db != nil {
				db.Close()
			}
		})
	}
}

func TestDatabase_InsertRawData(t *testing.T) {
	tdb := setupTestDatabase(t)
	defer tdb.teardownTestDatabase(t)

	tests := []struct {
		name    string
		data    *RawDataMessage
		wantErr bool
	}{
		{
			name: "valid data",
			data: &RawDataMessage{
				Source:   "test_source",
				SourceID: "test_id_1",
				Content: map[string]interface{}{
					"message": "test message",
					"value":   123,
				},
				Timestamp: time.Now(),
			},
			wantErr: false,
		},
		{
			name: "duplicate content hash",
			data: &RawDataMessage{
				Source:   "test_source",
				SourceID: "test_id_2",
				Content: map[string]interface{}{
					"message": "test message",
					"value":   123,
				},
				Timestamp: time.Now(),
			},
			wantErr: false, // Should not error on duplicate, just skip
		},
		{
			name: "empty source",
			data: &RawDataMessage{
				Source:   "",
				SourceID: "test_id_3",
				Content: map[string]interface{}{
					"message": "test message",
				},
				Timestamp: time.Now(),
			},
			wantErr: false, // Database doesn't enforce source validation
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			ctx := context.Background()
			err := tdb.InsertRawData(ctx, tt.data)
			if (err != nil) != tt.wantErr {
				t.Errorf("InsertRawData() error = %v, wantErr %v", err, tt.wantErr)
				return
			}

			if !tt.wantErr && tt.name != "duplicate content hash" && tt.data.ID == 0 {
				t.Error("Expected ID to be set after successful insert")
			}
		})
	}
}

func TestDatabase_GetRawDataByHash(t *testing.T) {
	tdb := setupTestDatabase(t)
	defer tdb.teardownTestDatabase(t)

	// Insert test data
	testData := &RawDataMessage{
		Source:   "test_source",
		SourceID: "test_id",
		Content: map[string]interface{}{
			"message": "test message for retrieval",
			"value":   456,
		},
		Timestamp: time.Now(),
	}

	ctx := context.Background()
	err := tdb.InsertRawData(ctx, testData)
	if err != nil {
		t.Fatalf("Failed to insert test data: %v", err)
	}

	tests := []struct {
		name        string
		contentHash string
		wantData    bool
		wantErr     bool
	}{
		{
			name:        "existing hash",
			contentHash: testData.ContentHash,
			wantData:    true,
			wantErr:     false,
		},
		{
			name:        "non-existing hash",
			contentHash: "non_existing_hash",
			wantData:    false,
			wantErr:     false,
		},
		{
			name:        "empty hash",
			contentHash: "",
			wantData:    false,
			wantErr:     false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			data, err := tdb.GetRawDataByHash(ctx, tt.contentHash)
			if (err != nil) != tt.wantErr {
				t.Errorf("GetRawDataByHash() error = %v, wantErr %v", err, tt.wantErr)
				return
			}

			if tt.wantData && data == nil {
				t.Error("Expected data to be returned")
			}

			if !tt.wantData && data != nil {
				t.Error("Expected no data to be returned")
			}

			if data != nil {
				if data.Source != testData.Source {
					t.Errorf("Expected source %s, got %s", testData.Source, data.Source)
				}
				if data.ContentHash != testData.ContentHash {
					t.Errorf("Expected hash %s, got %s", testData.ContentHash, data.ContentHash)
				}
			}
		})
	}
}

func TestDatabase_MarkAsProcessed(t *testing.T) {
	tdb := setupTestDatabase(t)
	defer tdb.teardownTestDatabase(t)

	// Insert test data
	testData := &RawDataMessage{
		Source:   "test_source",
		SourceID: "test_id",
		Content: map[string]interface{}{
			"message": "test message for processing",
		},
		Timestamp: time.Now(),
	}

	ctx := context.Background()
	err := tdb.InsertRawData(ctx, testData)
	if err != nil {
		t.Fatalf("Failed to insert test data: %v", err)
	}

	tests := []struct {
		name    string
		id      int64
		wantErr bool
	}{
		{
			name:    "valid id",
			id:      testData.ID,
			wantErr: false,
		},
		{
			name:    "non-existing id",
			id:      99999,
			wantErr: true,
		},
		{
			name:    "zero id",
			id:      0,
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := tdb.MarkAsProcessed(ctx, tt.id)
			if (err != nil) != tt.wantErr {
				t.Errorf("MarkAsProcessed() error = %v, wantErr %v", err, tt.wantErr)
			}
		})
	}
}

func TestDatabase_GetUnprocessedData(t *testing.T) {
	tdb := setupTestDatabase(t)
	defer tdb.teardownTestDatabase(t)

	// Insert test data
	testData := []*RawDataMessage{
		{
			Source:   "test_source",
			SourceID: "test_id_1",
			Content:  map[string]interface{}{"message": "unprocessed 1"},
			Timestamp: time.Now(),
		},
		{
			Source:   "test_source",
			SourceID: "test_id_2",
			Content:  map[string]interface{}{"message": "unprocessed 2"},
			Timestamp: time.Now(),
		},
	}

	ctx := context.Background()
	for _, data := range testData {
		err := tdb.InsertRawData(ctx, data)
		if err != nil {
			t.Fatalf("Failed to insert test data: %v", err)
		}
	}

	// Mark one as processed
	err := tdb.MarkAsProcessed(ctx, testData[0].ID)
	if err != nil {
		t.Fatalf("Failed to mark data as processed: %v", err)
	}

	tests := []struct {
		name      string
		limit     int
		offset    int
		wantCount int
		wantErr   bool
	}{
		{
			name:      "get all unprocessed",
			limit:     10,
			offset:    0,
			wantCount: 1, // Only one should be unprocessed
			wantErr:   false,
		},
		{
			name:      "limit results",
			limit:     1,
			offset:    0,
			wantCount: 1,
			wantErr:   false,
		},
		{
			name:      "offset results",
			limit:     10,
			offset:    1,
			wantCount: 0,
			wantErr:   false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			data, err := tdb.GetUnprocessedData(ctx, tt.limit, tt.offset)
			if (err != nil) != tt.wantErr {
				t.Errorf("GetUnprocessedData() error = %v, wantErr %v", err, tt.wantErr)
				return
			}

			if len(data) != tt.wantCount {
				t.Errorf("Expected %d records, got %d", tt.wantCount, len(data))
			}
		})
	}
}

func TestDatabase_HealthCheck(t *testing.T) {
	tdb := setupTestDatabase(t)
	defer tdb.teardownTestDatabase(t)

	ctx := context.Background()
	err := tdb.HealthCheck(ctx)
	if err != nil {
		t.Errorf("HealthCheck() error = %v", err)
	}
}

func TestDatabase_GetStats(t *testing.T) {
	tdb := setupTestDatabase(t)
	defer tdb.teardownTestDatabase(t)

	stats := tdb.GetStats()
	if stats == nil {
		t.Error("Expected stats to be returned")
	}

	expectedKeys := []string{
		"total_conns",
		"acquired_conns",
		"idle_conns",
		"max_conns",
		"acquire_count",
		"acquire_duration",
		"canceled_acquire_count",
	}

	for _, key := range expectedKeys {
		if _, exists := stats[key]; !exists {
			t.Errorf("Expected key %s in stats", key)
		}
	}
}

func TestDatabase_CleanupOldData(t *testing.T) {
	tdb := setupTestDatabase(t)
	defer tdb.teardownTestDatabase(t)

	// Insert and process test data
	testData := &RawDataMessage{
		Source:   "test_source",
		SourceID: "test_id",
		Content:  map[string]interface{}{"message": "old data"},
		Timestamp: time.Now().Add(-2 * time.Hour), // Old timestamp
	}

	ctx := context.Background()
	err := tdb.InsertRawData(ctx, testData)
	if err != nil {
		t.Fatalf("Failed to insert test data: %v", err)
	}

	// Mark as processed
	err = tdb.MarkAsProcessed(ctx, testData.ID)
	if err != nil {
		t.Fatalf("Failed to mark as processed: %v", err)
	}

	// Wait a moment to ensure processed_at timestamp is set
	time.Sleep(100 * time.Millisecond)

	// Test cleanup - use a very small duration to ensure the record is cleaned up
	deleted, err := tdb.CleanupOldData(ctx, 1*time.Millisecond)
	if err != nil {
		t.Errorf("CleanupOldData() error = %v", err)
	}

	if deleted != 1 {
		t.Errorf("Expected 1 record deleted, got %d", deleted)
	}
}

// Benchmark tests for performance validation
func BenchmarkDatabase_InsertRawData(b *testing.B) {
	tdb := setupTestDatabase(&testing.T{})
	defer tdb.teardownTestDatabase(&testing.T{})

	ctx := context.Background()
	
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		data := &RawDataMessage{
			Source:   "benchmark_source",
			SourceID: fmt.Sprintf("bench_id_%d", i),
			Content: map[string]interface{}{
				"message": fmt.Sprintf("benchmark message %d", i),
				"value":   i,
			},
			Timestamp: time.Now(),
		}
		
		err := tdb.InsertRawData(ctx, data)
		if err != nil {
			b.Fatalf("InsertRawData failed: %v", err)
		}
	}
}

func BenchmarkDatabase_HealthCheck(b *testing.B) {
	tdb := setupTestDatabase(&testing.T{})
	defer tdb.teardownTestDatabase(&testing.T{})

	ctx := context.Background()
	
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		err := tdb.HealthCheck(ctx)
		if err != nil {
			b.Fatalf("HealthCheck failed: %v", err)
		}
	}
}

// Test new functionality added for task 2.2

func TestDatabase_InsertRawDataBatch(t *testing.T) {
	tdb := setupTestDatabase(t)
	defer tdb.teardownTestDatabase(t)

	ctx := context.Background()

	tests := []struct {
		name    string
		data    []*RawDataMessage
		wantErr bool
	}{
		{
			name: "empty batch",
			data: []*RawDataMessage{},
			wantErr: false,
		},
		{
			name: "single record batch",
			data: []*RawDataMessage{
				{
					Source:   "batch_source",
					SourceID: "batch_id_1",
					Content: map[string]interface{}{
						"message": "batch message 1",
						"value":   100,
					},
					Timestamp: time.Now(),
				},
			},
			wantErr: false,
		},
		{
			name: "multiple records batch",
			data: []*RawDataMessage{
				{
					Source:   "batch_source",
					SourceID: "batch_id_2",
					Content: map[string]interface{}{
						"message": "batch message 2",
						"value":   200,
					},
					Timestamp: time.Now(),
				},
				{
					Source:   "batch_source",
					SourceID: "batch_id_3",
					Content: map[string]interface{}{
						"message": "batch message 3",
						"value":   300,
					},
					Timestamp: time.Now(),
				},
			},
			wantErr: false,
		},
		{
			name: "batch with duplicate content",
			data: []*RawDataMessage{
				{
					Source:   "batch_source",
					SourceID: "batch_id_4",
					Content: map[string]interface{}{
						"message": "duplicate message",
						"value":   400,
					},
					Timestamp: time.Now(),
				},
				{
					Source:   "batch_source",
					SourceID: "batch_id_5",
					Content: map[string]interface{}{
						"message": "duplicate message",
						"value":   400,
					},
					Timestamp: time.Now(),
				},
			},
			wantErr: false, // Should handle duplicates gracefully
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := tdb.InsertRawDataBatch(ctx, tt.data)
			if (err != nil) != tt.wantErr {
				t.Errorf("InsertRawDataBatch() error = %v, wantErr %v", err, tt.wantErr)
				return
			}

			// Verify records were inserted (for non-empty batches)
			if len(tt.data) > 0 && !tt.wantErr {
				for _, record := range tt.data {
					if record.ID == 0 {
						// Check if it was a duplicate (which is okay)
						existing, err := tdb.GetRawDataByHash(ctx, record.ContentHash)
						if err != nil {
							t.Errorf("Failed to check for existing record: %v", err)
						}
						if existing == nil {
							t.Error("Expected record to be inserted or already exist")
						}
					}
				}
			}
		})
	}
}

func TestDatabase_WithRetry(t *testing.T) {
	tdb := setupTestDatabase(t)
	defer tdb.teardownTestDatabase(t)

	ctx := context.Background()

	tests := []struct {
		name      string
		operation string
		fn        func() error
		wantErr   bool
	}{
		{
			name:      "successful operation",
			operation: "test_success",
			fn: func() error {
				return nil
			},
			wantErr: false,
		},
		{
			name:      "non-retryable error",
			operation: "test_non_retryable",
			fn: func() error {
				return &DatabaseError{
					Operation: "test",
					Err:       fmt.Errorf("validation error"),
					Retryable: false,
				}
			},
			wantErr: true,
		},
		{
			name:      "retryable error that eventually succeeds",
			operation: "test_retryable_success",
			fn: func() func() error {
				attempts := 0
				return func() error {
					attempts++
					if attempts < 2 {
						return &DatabaseError{
							Operation: "test",
							Err:       fmt.Errorf("temporary failure"),
							Retryable: true,
						}
					}
					return nil
				}
			}(),
			wantErr: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := tdb.WithRetry(ctx, tt.operation, tt.fn)
			if (err != nil) != tt.wantErr {
				t.Errorf("WithRetry() error = %v, wantErr %v", err, tt.wantErr)
			}
		})
	}
}

func TestDatabase_GetConnectionHealth(t *testing.T) {
	tdb := setupTestDatabase(t)
	defer tdb.teardownTestDatabase(t)

	ctx := context.Background()
	health := tdb.GetConnectionHealth(ctx)

	// Verify required health check fields
	requiredFields := []string{
		"ping_success",
		"pool_stats",
		"query_success",
		"table_access_success",
	}

	for _, field := range requiredFields {
		if _, exists := health[field]; !exists {
			t.Errorf("Expected health field %s to be present", field)
		}
	}

	// Verify ping success
	if pingSuccess, ok := health["ping_success"].(bool); !ok || !pingSuccess {
		t.Error("Expected ping_success to be true")
	}

	// Verify query success
	if querySuccess, ok := health["query_success"].(bool); !ok || !querySuccess {
		t.Error("Expected query_success to be true")
	}

	// Verify table access success
	if tableSuccess, ok := health["table_access_success"].(bool); !ok || !tableSuccess {
		t.Error("Expected table_access_success to be true")
	}

	// Verify pool stats structure
	if poolStats, ok := health["pool_stats"].(map[string]interface{}); ok {
		expectedPoolFields := []string{
			"total_conns",
			"acquired_conns",
			"idle_conns",
			"max_conns",
			"acquire_count",
			"acquire_duration_ms",
		}

		for _, field := range expectedPoolFields {
			if _, exists := poolStats[field]; !exists {
				t.Errorf("Expected pool stats field %s to be present", field)
			}
		}
	} else {
		t.Error("Expected pool_stats to be a map")
	}
}

func TestDatabase_ValidateSchema(t *testing.T) {
	tdb := setupTestDatabase(t)
	defer tdb.teardownTestDatabase(t)

	ctx := context.Background()
	err := tdb.ValidateSchema(ctx)
	if err != nil {
		t.Errorf("ValidateSchema() error = %v", err)
	}
}

func TestDatabaseError(t *testing.T) {
	tests := []struct {
		name      string
		err       *DatabaseError
		wantError string
		retryable bool
	}{
		{
			name: "retryable error",
			err: &DatabaseError{
				Operation: "test_operation",
				Err:       fmt.Errorf("connection failed"),
				Retryable: true,
			},
			wantError: "database operation 'test_operation' failed: connection failed",
			retryable: true,
		},
		{
			name: "non-retryable error",
			err: &DatabaseError{
				Operation: "validation",
				Err:       fmt.Errorf("invalid data"),
				Retryable: false,
			},
			wantError: "database operation 'validation' failed: invalid data",
			retryable: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if tt.err.Error() != tt.wantError {
				t.Errorf("DatabaseError.Error() = %v, want %v", tt.err.Error(), tt.wantError)
			}

			if tt.err.IsRetryable() != tt.retryable {
				t.Errorf("DatabaseError.IsRetryable() = %v, want %v", tt.err.IsRetryable(), tt.retryable)
			}

			// Test Unwrap
			if tt.err.Unwrap() == nil {
				t.Error("Expected Unwrap() to return the wrapped error")
			}
		})
	}
}

// Integration test for complete database workflow
func TestDatabase_CompleteWorkflow(t *testing.T) {
	tdb := setupTestDatabase(t)
	defer tdb.teardownTestDatabase(t)

	ctx := context.Background()

	// Test 1: Insert raw data
	testData := &RawDataMessage{
		Source:   "integration_test",
		SourceID: "integration_id_1",
		Content: map[string]interface{}{
			"message": "integration test message",
			"value":   999,
			"metadata": map[string]interface{}{
				"source_type": "test",
				"priority":    "high",
			},
		},
		Timestamp: time.Now(),
	}

	err := tdb.InsertRawData(ctx, testData)
	if err != nil {
		t.Fatalf("Failed to insert raw data: %v", err)
	}

	if testData.ID == 0 {
		t.Error("Expected ID to be set after insert")
	}

	// Test 2: Retrieve by hash
	retrieved, err := tdb.GetRawDataByHash(ctx, testData.ContentHash)
	if err != nil {
		t.Fatalf("Failed to retrieve data by hash: %v", err)
	}

	if retrieved == nil {
		t.Fatal("Expected to retrieve inserted data")
	}

	if retrieved.Source != testData.Source {
		t.Errorf("Expected source %s, got %s", testData.Source, retrieved.Source)
	}

	// Test 3: Check unprocessed data
	unprocessed, err := tdb.GetUnprocessedData(ctx, 10, 0)
	if err != nil {
		t.Fatalf("Failed to get unprocessed data: %v", err)
	}

	if len(unprocessed) == 0 {
		t.Error("Expected at least one unprocessed record")
	}

	// Test 4: Mark as processed
	err = tdb.MarkAsProcessed(ctx, testData.ID)
	if err != nil {
		t.Fatalf("Failed to mark as processed: %v", err)
	}

	// Test 5: Verify no unprocessed data
	unprocessedAfter, err := tdb.GetUnprocessedData(ctx, 10, 0)
	if err != nil {
		t.Fatalf("Failed to get unprocessed data after processing: %v", err)
	}

	if len(unprocessedAfter) >= len(unprocessed) {
		t.Error("Expected fewer unprocessed records after marking as processed")
	}

	// Test 6: Health check
	err = tdb.HealthCheck(ctx)
	if err != nil {
		t.Errorf("Health check failed: %v", err)
	}

	// Test 7: Get stats
	stats := tdb.GetStats()
	if stats == nil {
		t.Error("Expected stats to be returned")
	}

	// Test 8: Connection health
	health := tdb.GetConnectionHealth(ctx)
	if health == nil {
		t.Error("Expected connection health to be returned")
	}

	// Test 9: Schema validation
	err = tdb.ValidateSchema(ctx)
	if err != nil {
		t.Errorf("Schema validation failed: %v", err)
	}
}

// Performance test for batch operations
func BenchmarkDatabase_InsertRawDataBatch(b *testing.B) {
	tdb := setupTestDatabase(&testing.T{})
	defer tdb.teardownTestDatabase(&testing.T{})

	ctx := context.Background()
	batchSize := 10

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		batch := make([]*RawDataMessage, batchSize)
		for j := 0; j < batchSize; j++ {
			batch[j] = &RawDataMessage{
				Source:   "benchmark_batch",
				SourceID: fmt.Sprintf("batch_bench_id_%d_%d", i, j),
				Content: map[string]interface{}{
					"message": fmt.Sprintf("batch benchmark message %d-%d", i, j),
					"value":   i*batchSize + j,
				},
				Timestamp: time.Now(),
			}
		}

		err := tdb.InsertRawDataBatch(ctx, batch)
		if err != nil {
			b.Fatalf("InsertRawDataBatch failed: %v", err)
		}
	}
}