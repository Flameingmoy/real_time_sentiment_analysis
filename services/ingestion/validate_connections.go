package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"time"

	"github.com/IBM/sarama"
	"github.com/jackc/pgx/v5"
	"gopkg.in/yaml.v3"
)

type Config struct {
	Database struct {
		Host     string `yaml:"host"`
		Port     int    `yaml:"port"`
		Name     string `yaml:"name"`
		User     string `yaml:"user"`
		Password string `yaml:"password"`
	} `yaml:"database"`
	Kafka struct {
		Brokers []string `yaml:"brokers"`
	} `yaml:"kafka"`
}

func main() {
	// Load configuration
	configData, err := os.ReadFile("config.yaml")
	if err != nil {
		log.Fatalf("Failed to read config file: %v", err)
	}

	var config Config
	if err := yaml.Unmarshal(configData, &config); err != nil {
		log.Fatalf("Failed to parse config: %v", err)
	}

	fmt.Println("🔍 Validating service connections...")

	// Test PostgreSQL connection
	fmt.Print("📊 Testing PostgreSQL connection... ")
	dbURL := fmt.Sprintf("postgres://%s:%s@%s:%d/%s",
		config.Database.User,
		config.Database.Password,
		config.Database.Host,
		config.Database.Port,
		config.Database.Name)

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	conn, err := pgx.Connect(ctx, dbURL)
	if err != nil {
		fmt.Printf("❌ Failed: %v\n", err)
	} else {
		defer conn.Close(ctx)
		var result string
		err = conn.QueryRow(ctx, "SELECT 'PostgreSQL connection successful'").Scan(&result)
		if err != nil {
			fmt.Printf("❌ Query failed: %v\n", err)
		} else {
			fmt.Printf("✅ %s\n", result)
		}
	}

	// Test Kafka connection
	fmt.Print("📨 Testing Kafka connection... ")
	kafkaConfig := sarama.NewConfig()
	kafkaConfig.Version = sarama.V2_8_0_0
	kafkaConfig.Net.DialTimeout = 10 * time.Second

	client, err := sarama.NewClient(config.Kafka.Brokers, kafkaConfig)
	if err != nil {
		fmt.Printf("❌ Failed: %v\n", err)
	} else {
		defer client.Close()
		brokers := client.Brokers()
		fmt.Printf("✅ Connected to %d Kafka brokers\n", len(brokers))
	}

	fmt.Println("🎉 Connection validation complete!")
}