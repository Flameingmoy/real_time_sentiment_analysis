# Real-Time Sentiment Analysis System

A high-performance, scalable microservices architecture for real-time sentiment analysis of financial data streams using local AI models.

## 🎯 Project Overview

The Real-time Sentiment Analysis (RTSA) system processes financial data streams through a multi-stage pipeline, providing real-time sentiment insights from various data sources including market data, news, social media, and economic indicators. The system emphasizes performance, scalability, and real-time processing while maintaining data integrity and comprehensive monitoring capabilities.

### Key Features

- **Real-time Processing**: Sub-10 second sentiment analysis pipeline
- **Local AI Models**: Ollama `granite3.3:2b` for privacy and performance
- **Scalable Architecture**: Microservices with horizontal scaling capabilities
- **Multi-source Ingestion**: Support for various data sources via webhooks
- **Vector Similarity**: Redis-based content deduplication and similarity search
- **Comprehensive Monitoring**: Grafana dashboards with real-time metrics and alerting

## 🏗️ Architecture

The system is designed as a microservices architecture that processes financial data streams through a multi-stage pipeline. For a detailed explanation of the architecture, components, and data models, please see the [Design Document](./docs/design.md).

### High-Level Architecture

```mermaid
graph TB
    subgraph "External Data Sources"
        A[TrueData API]
        B[News APIs]
        C[Twitter API v2]
        D[Reddit API]
        E[Economic Data APIs]
    end
    
    subgraph "Ingestion Layer"
        F[Golang HTTP Server\nGin Framework]
        G[Rate Limiter]
        H[Data Validator]
    end
    
    subgraph "Storage Layer"
        I[(PostgreSQL-1\nRaw Data)]
        J[Apache Kafka\nMessage Queue]
        K[(Redis Vector Store\nEmbeddings)]
    end
    
    subgraph "Processing Layer"
        L[Python Sentiment Service]
        M[Ollama Granite 3.3\n2b/8b Local Model]
        N[System Prompt Handler]
        O[Response Parser]
    end
    
    subgraph "Analytics Layer"
        P[(PostgreSQL-2\nAnalytics)]
        Q[(PostgreSQL-3\nLogging)]
    end
    
    subgraph "Visualization Layer"
        R[Grafana Dashboards]
        S[Alert System]
    end
    
    A --> F
    B --> F
    C --> F
    D --> F
    E --> F
    
    F --> G
    G --> H
    H --> I
    H --> J
    
    J --> L
    L --> N
    N --> M
    M --> O
    O --> P
    O --> K
    
    P --> R
    Q --> R
    R --> S
    
    F --> Q
    L --> Q


### Service Communication

The system uses asynchronous communication through Kafka topics:

1. **Ingestion → Processing**: `sentiment_analysis_topic`
2. **Processing → Aggregation**: `aggregation_topic`  
3. **Alerts**: `alert_topic`

## 🚀 Quick Start

### Prerequisites

- **Docker & Docker Compose**: Ensure you have Docker and Docker Compose installed on your system.

### 1. Clone the Repository

```bash
git clone <repository-url>
cd real-time-sentiment-analysis
```

### 2. Start the Services

```bash
# Start all infrastructure services in detached mode
docker compose up -d
```

This command will build the necessary Docker images and start all the services defined in the `docker-compose.yml` file, including:
- Three PostgreSQL databases
- Kafka and Zookeeper
- Redis Stack
- Grafana
- The `ingestion` and `sentiment-analysis` services
- A setup container (`ollama-setup`) that downloads the required `granite3.3:2b` model.

### 3. Monitor the Setup

You can monitor the logs to see the progress of the setup, especially the model download.

```bash
# View the logs of all services
docker compose logs -f

# View the logs for a specific service (e.g., ollama-setup)
docker compose logs -f rtsa-ollama-setup
```

Once the `rtsa-ollama-setup` and `rtsa-kafka-setup` containers exit with code 0, the initial setup is complete.

### 4. Check Service Status

To ensure all services are running correctly, use the following command:

```bash
docker compose ps
```

You should see all services in the `running` or `healthy` state, except for the setup containers which should be `exited (0)`.

### 5. Access Services

Once everything is running, you can access the various services at the following endpoints:

- **Grafana Dashboard**: [http://localhost:3000](http://localhost:3000) (admin/admin)
- **Redis Insight**: [http://localhost:8002](http://localhost:8002)
- **Ingestion Service**: [http://localhost:8081](http://localhost:8081)
- **Sentiment Analysis Service**: [http://localhost:8000](http://localhost:8000)
- **Ollama API**: [http://localhost:11435](http://localhost:11435)
- **Kafka Broker**: `localhost:9092`
- **PostgreSQL Databases**:
  - **Raw Data**: `psql -h localhost -p 5433 -U rtsa_user -d rtsa_raw`
  - **Analytics**: `psql -h localhost -p 5434 -U rtsa_user -d rtsa_analytics`
  - **Logging**: `psql -h localhost -p 5435 -U rtsa_user -d rtsa_logging`

## 🔧 Configuration

The system is configured using environment variables within the `docker-compose.yml` file and service-specific configuration files.

- **Go Ingestion Service**: Configuration is managed through [`services/ingestion/config.yaml`](./services/ingestion/config.yaml).
- **Python Sentiment Analysis Service**: Environment variables for this service can be defined in [`services/sentiment-analysis/.env`](./services/sentiment-analysis/.env) for local development. In the Docker environment, these are set directly in the `docker-compose.yml`.

## 🗄️ Database Schema

The database schemas for the PostgreSQL instances are defined in the SQL initialization scripts located in the `/sql` directory. For a detailed breakdown of the table structures, indexes, and views, please refer to the [Database Design section in the Design Document](./docs/design.md#database-design).

## 🧪 Testing

The repository includes connection validation scripts for each service (`validate_connections.go` and `validate_connections.py`). These are used as health checks within the Docker containers to ensure that services can connect to their dependencies.

## 📊 Monitoring

### Grafana Dashboards

Access Grafana at http://localhost:3000 with credentials `admin/admin`. Pre-configured dashboards include:

- **System Overview**: Service health and performance metrics
- **Ingestion Metrics**: Request rates, response times, error rates
- **Sentiment Analysis**: Processing times, model performance, accuracy metrics
- **Data Flow**: Message queue metrics, processing pipeline status

### Key Metrics

- **Throughput**: Messages processed per second
- **Latency**: End-to-end processing time (target: <10s)
- **Accuracy**: Sentiment classification confidence scores
- **Error Rates**: Failed requests and processing errors
- **Resource Usage**: CPU, memory, and storage utilization

## 🔒 Security Considerations

- **Local AI Models**: No data sent to external AI services
- **Database Security**: Isolated databases with proper access controls
- **Rate Limiting**: Protection against API abuse
- **Input Validation**: Comprehensive data sanitization
- **Network Security**: Services communicate through internal networks

## 🚀 Deployment

### Development
```bash
# Start infrastructure
docker compose up -d

# Run services locally
cd services/ingestion && go run main.go
cd services/sentiment-analysis && python main.py
```

### Production
- Use Docker containers for all services
- Implement proper secrets management
- Configure monitoring and alerting
- Set up backup and disaster recovery
- Implement CI/CD pipelines

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For questions and support:
- Check the [design document](.kiro/specs/real-time-sentiment-analysis/design.md) for detailed architecture information
- Review [requirements](.kiro/specs/real-time-sentiment-analysis/requirements.md) for feature specifications
- Check [tasks](.kiro/specs/real-time-sentiment-analysis/tasks.md) for implementation progress

## 🔄 Development Status

The project is currently in the setup and infrastructure phase. All services can be started via Docker Compose, but the core application logic for the ingestion and sentiment analysis services is still under development.

- ✅ Infrastructure Setup (Databases, Kafka, Redis, Ollama)
- ✅ Service containerization
- ✅ Automated model download
- 🚧 Core Service Implementation (In Progress)
- ⏳ API Integration
- ⏳ Testing and Optimization
- ⏳ Monitoring and Alerting Setup
