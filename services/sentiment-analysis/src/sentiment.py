"""Sentiment analysis using Ollama Granite 3.3"""

import asyncio
import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

import ollama
from ollama import AsyncClient

@dataclass
class SentimentResult:
    """Result of sentiment analysis"""
    sentiment: str  # 'positive', 'negative', 'neutral'
    score: float  # confidence score 0-1
    confidence: float  # overall confidence
    entities: List[Dict[str, Any]]  # detected entities
    summary: str  # brief summary of sentiment
    timestamp: datetime

@dataclass
class FinancialSentiment:
    """Financial-specific sentiment analysis"""
    market_sentiment: str  # bullish, bearish, neutral
    financial_entities: List[str]  # stocks, currencies, commodities
    risk_level: str  # low, medium, high
    time_horizon: str  # short-term, medium-term, long-term
    trading_signal: str  # buy, sell, hold

class SentimentAnalyzer:
    """Ollama-based sentiment analyzer"""
    
    def __init__(self, config):
        self.config = config
        self.client = None
        self.model = config.model
        self.logger = logging.getLogger(__name__)
        
    async def initialize(self):
        """Initialize Ollama client"""
        self.client = AsyncClient(host=f"http://{self.config.host}:{self.config.port}")
        self.logger.info(f"Initialized Ollama client with model: {self.model}")
    
    async def health_check(self):
        """Check Ollama connection"""
        try:
            response = await self.client.list()
            models = [m['name'] for m in response['models']]
            if self.model not in models:
                raise Exception(f"Model {self.model} not found in available models: {models}")
            return True
        except Exception as e:
            self.logger.error(f"Ollama health check failed: {e}")
            raise
    
    async def close(self):
        """Close Ollama client"""
        if self.client:
            # Ollama client doesn't have explicit close method
            self.client = None
    
    async def analyze_sentiment(self, text: str) -> SentimentResult:
        """Analyze sentiment of given text"""
        
        prompt = self._build_sentiment_prompt(text)
        
        try:
            response = await self.client.generate(
                model=self.model,
                prompt=prompt,
                stream=False,
                options={
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "max_tokens": 512
                }
            )
            
            # Parse response
            result = self._parse_sentiment_response(response['response'])
            return result
            
        except Exception as e:
            self.logger.error(f"Sentiment analysis failed: {e}")
            raise
    
    async def analyze_financial_sentiment(self, text: str) -> FinancialSentiment:
        """Analyze financial-specific sentiment"""
        
        prompt = self._build_financial_sentiment_prompt(text)
        
        try:
            response = await self.client.generate(
                model=self.model,
                prompt=prompt,
                stream=False,
                options={
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "max_tokens": 512
                }
            )
            
            # Parse response
            result = self._parse_financial_sentiment_response(response['response'])
            return result
            
        except Exception as e:
            self.logger.error(f"Financial sentiment analysis failed: {e}")
            raise
    
    def _build_sentiment_prompt(self, text: str) -> str:
        """Build sentiment analysis prompt"""
        return f"""
        Analyze the following text for sentiment. Provide a JSON response with:
        - sentiment: one of "positive", "negative", "neutral"
        - score: confidence score between 0 and 1
        - confidence: overall confidence in the analysis
        - entities: list of relevant entities mentioned (stocks, companies, people, etc.)
        - summary: brief 1-2 sentence summary of the sentiment
        
        Text: {text}
        
        Respond only with valid JSON in this format:
        {{
            "sentiment": "positive|negative|neutral",
            "score": 0.8,
            "confidence": 0.9,
            "entities": [{{"type": "company", "name": "Apple", "sentiment": "positive"}}],
            "summary": "The text expresses positive sentiment about technology stocks."
        }}
        """
    
    def _build_financial_sentiment_prompt(self, text: str) -> str:
        """Build financial sentiment analysis prompt"""
        return f"""
        Analyze the following financial text for trading insights. Provide a JSON response with:
        - market_sentiment: one of "bullish", "bearish", "neutral"
        - financial_entities: list of financial entities (stocks, currencies, commodities)
        - risk_level: one of "low", "medium", "high"
        - time_horizon: one of "short-term", "medium-term", "long-term"
        - trading_signal: one of "buy", "sell", "hold"
        
        Text: {text}
        
        Respond only with valid JSON in this format:
        {{
            "market_sentiment": "bullish",
            "financial_entities": ["AAPL", "USD", "Gold"],
            "risk_level": "medium",
            "time_horizon": "medium-term",
            "trading_signal": "buy"
        }}
        """
    
    def _parse_sentiment_response(self, response: str) -> SentimentResult:
        """Parse sentiment analysis response"""
        try:
            # Clean response
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            data = json.loads(response)
            
            return SentimentResult(
                sentiment=data.get('sentiment', 'neutral'),
                score=float(data.get('score', 0.5)),
                confidence=float(data.get('confidence', 0.5)),
                entities=data.get('entities', []),
                summary=data.get('summary', ''),
                timestamp=datetime.utcnow()
            )
            
        except (json.JSONDecodeError, KeyError) as e:
            self.logger.error(f"Failed to parse sentiment response: {e}")
            # Return neutral sentiment as fallback
            return SentimentResult(
                sentiment='neutral',
                score=0.5,
                confidence=0.1,
                entities=[],
                summary='Failed to parse response',
                timestamp=datetime.utcnow()
            )
    
    def _parse_financial_sentiment_response(self, response: str) -> FinancialSentiment:
        """Parse financial sentiment analysis response"""
        try:
            # Clean response
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            data = json.loads(response)
            
            return FinancialSentiment(
                market_sentiment=data.get('market_sentiment', 'neutral'),
                financial_entities=data.get('financial_entities', []),
                risk_level=data.get('risk_level', 'medium'),
                time_horizon=data.get('time_horizon', 'medium-term'),
                trading_signal=data.get('trading_signal', 'hold')
            )
            
        except (json.JSONDecodeError, KeyError) as e:
            self.logger.error(f"Failed to parse financial sentiment response: {e}")
            # Return neutral sentiment as fallback
            return FinancialSentiment(
                market_sentiment='neutral',
                financial_entities=[],
                risk_level='medium',
                time_horizon='medium-term',
                trading_signal='hold'
            )
    
    async def analyze_batch(self, texts: List[str]) -> List[SentimentResult]:
        """Analyze multiple texts in batch"""
        tasks = [self.analyze_sentiment(text) for text in texts]
        return await asyncio.gather(*tasks)
    
    async def analyze_with_context(self, text: str, context: Dict[str, Any]) -> SentimentResult:
        """Analyze text with additional context"""
        
        context_prompt = f"""
        Analyze the following text considering the provided context:
        
        Text: {text}
        
        Context: {json.dumps(context, indent=2)}
        
        Provide a JSON response with:
        - sentiment: one of "positive", "negative", "neutral"
        - score: confidence score between 0 and 1
        - confidence: overall confidence in the analysis
        - entities: list of relevant entities mentioned
        - summary: brief 1-2 sentence summary
        - context_impact: how context affects sentiment
        
        Respond only with valid JSON.
        """
        
        try:
            response = await self.client.generate(
                model=self.model,
                prompt=context_prompt,
                stream=False,
                options={
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "max_tokens": 512
                }
            )
            
            return self._parse_sentiment_response(response['response'])
            
        except Exception as e:
            self.logger.error(f"Context-aware sentiment analysis failed: {e}")
            raise
