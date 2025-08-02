#!/usr/bin/env python3
"""
Real-time Sentiment Analysis Service
Processes messages from Kafka and performs sentiment analysis using Ollama Granite 3.3
"""

import asyncio
import json
import logging
import os
import signal
import sys
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import uvicorn

from src.consumer import KafkaConsumerService
from src.sentiment import SentimentAnalyzer
from src.database import AnalyticsDatabase
from src.vector_store import VectorStore
from src.config import Config

import prometheus_client
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('sentiment_analysis.log')
    ]
)
logger = logging.getLogger(__name__)

def start_metrics_server(port: int):
    """Start the Prometheus metrics server in a separate thread."""
    prometheus_client.start_http_server(port)

class SentimentAnalysisService:
    """Main sentiment analysis service"""
    
    def __init__(self):
        self.config = Config()
        self.consumer = None
        self.analyzer = None
        self.database = None
        self.vector_store = None
        self.app = FastAPI(title="Sentiment Analysis Service", version="1.0.0")
        self.setup_routes()
        self.running = False
        
    def setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            health_status = {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "services": {}
            }
            
            # Check database connection
            try:
                if self.database:
                    await self.database.health_check()
                    health_status["services"]["database"] = "healthy"
                else:
                    health_status["services"]["database"] = "uninitialized"
            except Exception as e:
                health_status["services"]["database"] = f"unhealthy: {str(e)}"
                
            # Check Ollama connection
            try:
                if self.analyzer:
                    await self.analyzer.health_check()
                    health_status["services"]["ollama"] = "healthy"
                else:
                    health_status["services"]["ollama"] = "uninitialized"
            except Exception as e:
                health_status["services"]["ollama"] = f"unhealthy: {str(e)}"
                
            # Check vector store
            try:
                if self.vector_store:
                    await self.vector_store.health_check()
                    health_status["services"]["vector_store"] = "healthy"
                else:
                    health_status["services"]["vector_store"] = "uninitialized"
            except Exception as e:
                health_status["services"]["vector_store"] = f"unhealthy: {str(e)}"
                
            return health_status
            
        @self.app.post("/analyze")
        async def analyze_text(text: str, background_tasks: BackgroundTasks):
            """Direct text analysis endpoint for testing"""
            if not self.analyzer:
                raise HTTPException(status_code=503, detail="Analyzer not initialized")
                
            try:
                result = await self.analyzer.analyze_sentiment(text)
                return {
                    "text": text,
                    "sentiment": result.sentiment,
                    "score": result.score,
                    "confidence": result.confidence,
                    "entities": result.entities,
                    "timestamp": datetime.utcnow().isoformat()
                }
            except Exception as e:
                logger.error(f"Error analyzing text: {e}")
                raise HTTPException(status_code=500, detail=str(e))
    
    async def initialize_services(self):
        """Initialize all service components"""
        try:
            logger.info("Initializing sentiment analysis service...")
            
            # Initialize database
            self.database = AnalyticsDatabase(self.config.database_config)
            await self.database.initialize()
            logger.info("Database initialized successfully")
            
            # Initialize vector store
            self.vector_store = VectorStore(self.config.redis_config)
            await self.vector_store.initialize()
            logger.info("Vector store initialized successfully")
            
            # Initialize sentiment analyzer
            self.analyzer = SentimentAnalyzer(self.config.ollama_config)
            await self.analyzer.initialize()
            logger.info("Sentiment analyzer initialized successfully")
            
            # Initialize Kafka consumer
            self.consumer = KafkaConsumerService(
                self.config.kafka_config,
                self.analyzer,
                self.database,
                self.vector_store
            )
            logger.info("Kafka consumer initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            raise
    
    async def start_processing(self):
        """Start processing messages from Kafka"""
        if not self.consumer:
            logger.error("Consumer not initialized")
            return
            
        try:
            logger.info("Starting message processing...")
            await self.consumer.start_consuming()
        except Exception as e:
            logger.error(f"Error during message processing: {e}")
            raise
    
    async def shutdown(self):
        """Gracefully shutdown all services"""
        logger.info("Shutting down sentiment analysis service...")
        self.running = False
        
        if self.consumer:
            await self.consumer.stop_consuming()
            
        if self.database:
            await self.database.close()
            
        if self.vector_store:
            await self.vector_store.close()
            
        if self.analyzer:
            await self.analyzer.close()
            
        logger.info("Service shutdown complete")

async def main():
    """Main application entry point"""
    service = SentimentAnalysisService()
    
    try:
        # Initialize services
        await service.initialize_services()
        
        # Setup signal handlers
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            asyncio.create_task(service.shutdown())
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Start processing in background
        processing_task = asyncio.create_task(service.start_processing())
        
        # Start FastAPI server
        config = service.config
        logger.info(f"Starting FastAPI server on {config.server_config['host']}:{config.server_config['port']}")
        
        server_config = uvicorn.Config(
            service.app,
            host=config.server_config['host'],
            port=config.server_config['port'],
            log_level="info"
        )
        server = uvicorn.Server(server_config)
        
        # Run both server and processing
        await asyncio.gather(
            server.serve(),
            processing_task
        )
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        await service.shutdown()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
