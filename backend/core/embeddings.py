# backend/core/embeddings.py
import logging
from backend.services.ollama_service import OllamaService
from backend.config import settings

logger = logging.getLogger(__name__)

class EmbeddingGenerator:
    def __init__(self):
        # Ensure the model used here is appropriate for generating embeddings.
        # Some models are chat/text generation focused, others are specifically for embeddings.
        # The GRANITE_MODEL environment variable should point to an embedding-capable model.
        self.ollama_service = OllamaService()

    async def generate_embeddings(self, text: str) -> list[float] | None:
        """
        Generates semantic embeddings for a given text.
        Returns a list of floats representing the embedding, or None if an error occurs.
        """
        if not await self.ollama_service.check_model_availability():
            logger.error(f"Ollama model {self.ollama_service.model} not available. Cannot generate embeddings.")
            return None

        try:
            logger.info(f"Generating embeddings for text: '{text[:50]}...'" )
            embeddings = await self.ollama_service.generate_embeddings(text_input=text)
            
            if embeddings:
                logger.info(f"Successfully generated embeddings. Dimension: {len(embeddings)}")
                return embeddings
            else:
                logger.warning(f"Received no embeddings for text: '{text[:50]}...'. Model might not support embeddings or input was empty.")
                return None
        except Exception as e:
            logger.error(f"Error during embedding generation: {e}")
            return None

# Example Usage (for testing this module directly)
if __name__ == "__main__":
    import asyncio

    async def test_embeddings():
        generator = EmbeddingGenerator()

        # Ensure your .env file is set up and Ollama is running with an embedding-capable Granite model
        print(f"Using Ollama base URL: {settings.OLLAMA_BASE_URL} and model: {settings.GRANITE_MODEL}")
        
        # It's crucial that the GRANITE_MODEL specified in your .env (or default)
        # is one that actually produces embeddings via the /api/embeddings endpoint in Ollama.
        # Not all generative models do. You might need a specific model like 'nomic-embed-text' or ensure
        # your 'granite' model is an embedder.
        
        test_texts = [
            "This is a sample sentence to generate embeddings for.",
            "Customer feedback analysis is becoming increasingly important for businesses.",
            "The quick brown fox jumps over the lazy dog."
        ]

        for text in test_texts:
            print(f"\nGenerating embeddings for: '{text}'")
            result = await generator.generate_embeddings(text)
            if result:
                print(f"Embeddings (first 5 dimensions): {result[:5]}")
                print(f"Total dimensions: {len(result)}")
            else:
                print("Failed to generate embeddings.")
            
    # asyncio.run(test_embeddings()) # Uncomment to run test
