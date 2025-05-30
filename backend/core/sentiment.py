# backend/core/sentiment.py
import logging
from backend.services.ollama_service import OllamaService
from backend.config import settings

logger = logging.getLogger(__name__)

class SentimentAnalyzer:
    def __init__(self):
        self.ollama_service = OllamaService()
        # Define a system prompt that guides the LLM to output structured sentiment
        # This might need refinement based on the model's behavior
        self.sentiment_system_prompt = """
        Analyze the sentiment of the following text.
        Classify the sentiment as 'positive', 'negative', or 'neutral'.
        Optionally, you can also provide a confidence score from 0 to 1.
        Return the result in JSON format, for example:
        {"sentiment": "positive", "confidence": 0.9}
        Or if confidence is not applicable:
        {"sentiment": "neutral"}
        """

    async def analyze_sentiment(self, text: str) -> dict:
        """
        Analyzes the sentiment of a given text.
        Returns a dictionary with sentiment classification (e.g., {"sentiment": "positive", "confidence": 0.9}).
        """
        if not await self.ollama_service.check_model_availability():
            logger.error(f"Ollama model {self.ollama_service.model} not available. Cannot analyze sentiment.")
            # Return a default or error state
            return {"error": "Model not available"}

        try:
            logger.info(f"Analyzing sentiment for text: '{text[:50]}...'" )
            # Using the generate_text method from OllamaService
            # The prompt is the text itself, and we provide the system_prompt for structure
            response_data = await self.ollama_service.generate_text(
                prompt=text,
                system_prompt=self.sentiment_system_prompt,
                stream=False # Expecting a single JSON response
            )
            
            raw_response_text = response_data.get("response")
            if raw_response_text:
                # Attempt to parse the LLM's response (expected to be JSON)
                import json
                try:
                    sentiment_result = json.loads(raw_response_text)
                    logger.info(f"Successfully parsed sentiment: {sentiment_result}")
                    return sentiment_result
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse sentiment JSON from LLM response: {raw_response_text}")
                    # Fallback or error handling if parsing fails
                    return {"error": "Failed to parse sentiment response", "raw_response": raw_response_text}
            else:
                logger.error("No response text received from Ollama for sentiment analysis.")
                return {"error": "No response from model"}

        except Exception as e:
            logger.error(f"Error during sentiment analysis: {e}")
            return {"error": str(e)}

# Example Usage (for testing this module directly)
if __name__ == "__main__":
    import asyncio

    async def test_sentiment():
        analyzer = SentimentAnalyzer()
        
        # Ensure your .env file is set up and Ollama is running with the Granite model
        print(f"Using Ollama base URL: {settings.OLLAMA_BASE_URL} and model: {settings.GRANITE_MODEL}")

        test_texts = [
            "I love this product, it's amazing!",
            "This is the worst service I have ever experienced.",
            "The weather today is quite pleasant.",
            "The meeting was rescheduled to 3 PM."
        ]

        for text in test_texts:
            print(f"\nAnalyzing: '{text}'")
            result = await analyzer.analyze_sentiment(text)
            print(f"Result: {result}")
            
    # asyncio.run(test_sentiment()) # Uncomment to run test
