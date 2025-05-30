# backend/services/sentiment_service.py
import httpx
import json
import logging
from typing import Dict, Any

from backend.config import settings

logger = logging.getLogger(__name__)

# Use the specific model name you provided
OLLAMA_MODEL_NAME = "granite3.3:8b"

async def analyze_sentiment(text_content: str) -> Dict[str, Any]:
    """
    Analyzes sentiment of the given text using Ollama and a specified Granite model.
    Instructs the model to return a JSON object with 'sentiment_label' and 'sentiment_score'.
    """
    prompt = f"""Analyze the sentiment of the following text and return your response as a JSON object with two keys: 'sentiment_label' (string, e.g., 'positive', 'negative', 'neutral') and 'sentiment_score' (float, between 0.0 and 1.0, where 1.0 is very positive and 0.0 is very negative). Only return the JSON object.

Text: "{text_content}"

JSON Response:"""

    ollama_api_url = f"{settings.OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": OLLAMA_MODEL_NAME, # Using the specific model name
        "prompt": prompt,
        "stream": False, # We want the full response, not a stream
        "format": "json" # Request JSON output from Ollama if the model supports it directly
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client: # Added timeout
            response = await client.post(ollama_api_url, json=payload)
            response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
            
            ollama_response_text = response.text
            # Ollama's /api/generate with format:json often wraps the JSON in its own structure.
            # We need to parse the top-level JSON and then extract the model's actual JSON output.
            try:
                full_ollama_json = json.loads(ollama_response_text)
                model_json_output_str = full_ollama_json.get("response", "{}")
                # The model's response itself should be a JSON string, parse it again.
                sentiment_data = json.loads(model_json_output_str)
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding JSON from Ollama response: {e}")
                logger.error(f"Ollama raw response text: {ollama_response_text}")
                # Fallback or default sentiment if parsing fails
                return {
                    "sentiment_label": "error_parsing_model_output",
                    "sentiment_score": None,
                    "model_used": OLLAMA_MODEL_NAME
                }

        # Validate the structure of sentiment_data
        if not isinstance(sentiment_data, dict) or \
           "sentiment_label" not in sentiment_data or \
           "sentiment_score" not in sentiment_data:
            logger.error(f"Unexpected JSON structure from model: {sentiment_data}")
            return {
                "sentiment_label": "error_unexpected_model_structure",
                "sentiment_score": None,
                "model_used": OLLAMA_MODEL_NAME
            }

        return {
            "sentiment_label": str(sentiment_data.get("sentiment_label", "unknown")),
            "sentiment_score": float(sentiment_data.get("sentiment_score", 0.0)) if sentiment_data.get("sentiment_score") is not None else None,
            "model_used": OLLAMA_MODEL_NAME
        }

    except httpx.RequestError as e:
        logger.error(f"HTTP request error calling Ollama: {e}")
        # Fallback sentiment in case of Ollama connection error
        return {
            "sentiment_label": "error_ollama_connection",
            "sentiment_score": None,
            "model_used": OLLAMA_MODEL_NAME
        }
    except Exception as e:
        logger.error(f"An unexpected error occurred during sentiment analysis: {e}")
        return {
            "sentiment_label": "error_unexpected",
            "sentiment_score": None,
            "model_used": OLLAMA_MODEL_NAME
        }
