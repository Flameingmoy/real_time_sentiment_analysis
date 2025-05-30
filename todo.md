# Real-Time Customer Feedback Sentiment Analysis System - ToDo

## Phase 1: Project Setup & Core Backend
- [ ] **Environment Setup**
  - [ ] Install Python 3.11+

  - [ ] Install and configure PostgreSQL 14+ with pgvector extension
  - [ ] Install and configure Redis 6+
  - [ ] Install and configure Ollama with IBM Granite models
  - [ ] Set up Conda environment (optional, but recommended)
- [x] **Backend Initialization (FastAPI)**
  - [x] Create project directory structure (`backend`, `frontend`, `docs`, etc.)
  - [x] Initialize FastAPI project within `backend`
  - [x] Configure basic logging
  - [x] Set up `.env` file for configuration management
- [x] **Core Sentiment Analysis & Embeddings**
  - [In Progress] Implement Ollama client for interacting with Granite models
  - [x] Develop module for sentiment analysis
  - [x] Develop module for generating semantic embeddings
- [ ] **Database Integration (PostgreSQL & pgvector)**
  - [x] Define database schema (tables for feedback, sentiment results, embeddings)
  - [x] Implement SQLAlchemy models (or other ORM/DB connector)
  - [ ] Set up Alembic for database migrations
  - [ ] Implement functions for storing and retrieving feedback, sentiment, and embeddings
- [x] **Basic API Endpoints**
  - [x] Endpoint to submit new feedback (text input)
  - [x] Endpoint to get sentiment and embeddings for submitted feedback
  - [x] Endpoint to list all feedback with their analyses

## Phase 2: Data Ingestion & Advanced Processing
- [ ] **Data Ingestion Modules**
  - [ ] Implement CSV file ingestion (upload or watch directory)
  - [ ] Implement webhook endpoint for real-time data ingestion
  - [ ] Design and implement a common data model for ingested feedback
- [ ] **Asynchronous Processing (Optional - based on discussion)**
  - [ ] Evaluate need for Kafka/Celery for high-volume ingestion
  - [ ] (If needed) Integrate Kafka for message queuing
  - [ ] (If needed) Implement background workers for processing queued feedback
- [ ] **Topic Extraction**
  - [ ] Research and select a topic modeling technique (e.g., LDA, BERTopic with embeddings)
  - [ ] Implement topic extraction module
  - [ ] Store extracted topics in the database
  - [ ] API endpoint to get topics for a given feedback or overall trends

## Phase 3: Frontend Dashboard & Real-time Features
- [ ] **Frontend Initialization (Streamlit)**
  - [ ] Initialize Streamlit application within `frontend` directory
- [ ] **UI Components for Core Data Display**
  - [ ] Component to submit new feedback
  - [ ] Component to display list of feedback with sentiment scores
  - [ ] Component to show detailed view of a feedback item (text, sentiment, topics, similar items)
- [ ] **Real-time Integration (WebSockets)**
  - [ ] Implement WebSocket endpoint in FastAPI backend
  - [ ] Implement WebSocket handling in Streamlit frontend
  - [ ] Push real-time updates for new feedback analysis to the dashboard
- [ ] **Analytics & Visualizations**
  - [ ] Chart for sentiment trends over time (e.g., line chart)
  - [ ] Visualization for topic distribution (e.g., bar chart, word cloud)
  - [ ] Interface for semantic similarity search (input text, display similar feedback)
- [ ] **Data Source Integration Panel**
  - [ ] UI for managing CSV uploads
  - [ ] Display information/setup for webhook integration

## Phase 4: Alerting System
- [ ] **Backend Alerting Logic**
  - [ ] Define alert conditions (e.g., high negative sentiment spike, specific keywords)
  - [ ] Implement logic to check for alert conditions
  - [ ] Integrate email notification service (e.g., SendGrid, SMTP)
- [ ] **API Endpoints for Alerts**
  - [ ] Endpoint to create/configure alert rules
  - [ ] Endpoint to list/manage existing alerts
- [ ] **Frontend Alert Management Interface**
  - [ ] UI for users to define and manage alert rules
  - [ ] Display triggered alerts on the dashboard

## Phase 5: Dockerization, Testing & Finalization
- [ ] **Containerization (Docker)**
  - [ ] Create `Dockerfile` for the backend
  - [ ] Create `Dockerfile` for the frontend
  - [ ] Create `docker-compose.yml` for multi-container application (backend, frontend, postgres, redis, ollama)
- [ ] **Testing**
  - [ ] Write unit tests for backend modules (sentiment, embeddings, data ingestion)
  - [ ] Write integration tests for API endpoints
  - [ ] Write tests for Streamlit application (if applicable/using a testing framework for Streamlit)
  - [ ] Perform end-to-end testing of key user flows
- [ ] **Documentation**
  - [ ] Update `README.md` with detailed setup and usage instructions (local and Docker)
  - [ ] Add API documentation (e.g., using FastAPI's automatic docs, or tools like Swagger/OpenAPI)
  - [ ] Document system architecture and design choices in `Real-Time Customer Feedback Sentiment Analysis System.md`
- [ ] **Final Review & Delivery**
  - [ ] Code review and refactoring
  - [ ] Ensure all prerequisites and dependencies are clearly listed
  - [ ] Prepare for final delivery to the user

## Future Enhancements (Optional)
- [ ] User authentication and authorization
- [ ] More sophisticated topic modeling and trend analysis
- [ ] Support for more data sources (e.g., social media, APIs)
- [ ] Customizable dashboards
- [ ] Advanced reporting features
