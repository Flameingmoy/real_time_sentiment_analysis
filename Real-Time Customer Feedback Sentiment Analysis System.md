# Real-Time Customer Feedback Sentiment Analysis System

## Project Overview

This system provides real-time sentiment analysis of customer feedback across multiple channels, with powerful analytics and visualizations. It leverages IBM Granite models and granite embeddings via Ollama for high-quality sentiment analysis and semantic embeddings.

## Key Features

- **Multi-source Data Ingestion**: Ingest feedback from CSV files, webhooks, and more
- **Real-time Sentiment Analysis**: Analyze sentiment using IBM Granite models
- **Semantic Embeddings**: Generate and search embeddings for semantic similarity
- **Topic Extraction**: Identify key topics in customer feedback
- **Real-time Dashboard**: Visualize sentiment trends and analytics
- **WebSocket Integration**: Get real-time updates on the dashboard

## System Architecture

The system follows a modular architecture with the following key components:

1. **Backend (FastAPI)**
   - Data ingestion from multiple sources (CSV, webhooks, etc.)
   - Sentiment analysis using IBM Granite models via Ollama
   - Semantic embeddings for similarity search
   - Real-time processing with WebSocket support
   - RESTful API endpoints for data access

2. **Frontend (Streamlit)**
   - Real-time dashboard with sentiment analytics
   - Interactive visualizations for sentiment trends and topic distribution
   - Data source integration panel

3. **Database & Messaging**
   - PostgreSQL with pgvector extension for vector search
   - Redis for caching and real-time data
   - Kafka for message processing


