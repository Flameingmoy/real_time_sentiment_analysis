import httpx
import logging
from backend.config import settings

logger = logging.getLogger(__name__)

class OllamaService:
    def __init__(self, base_url: str = None, model: str = None):
        self.base_url = base_url if base_url is not None else settings.OLLAMA_BASE_URL
        self.model = model if model is not None else settings.GRANITE_MODEL
        self.api_generate_url = f"{self.base_url}/api/generate"
        self.api_embeddings_url = f"{self.base_url}/api/embeddings"

    async def _make_request(self, url: str, payload: dict) -> dict:
        """Helper function to make asynchronous POST requests to Ollama."""
        async with httpx.AsyncClient(timeout=60.0) as client: # Increased timeout for potentially long model responses
            try:
                logger.info(f"Sending request to Ollama URL: {url} with model: {payload.get('model')}")
                response = await client.post(url, json=payload)
                response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)
                logger.info(f"Received successful response from Ollama URL: {url}")
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
                # Consider how to handle different errors, e.g., model not found, server error
                raise
            except httpx.RequestError as e:
                logger.error(f"Request error occurred: {e}")
                # E.g., network issue, Ollama server not reachable
                raise
            except Exception as e:
                logger.error(f"An unexpected error occurred: {e}")
                raise

    async def generate_text(self, prompt: str, system_prompt: str = None, stream: bool = False) -> dict:
        """
        Generates text using the specified model.
        For sentiment analysis, the prompt will be the customer feedback,
        and system_prompt can be used to instruct the model on the desired output format.
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream
        }
        if system_prompt:
            payload["system"] = system_prompt
        
        # Ollama's /api/generate returns a stream of JSON objects if stream=True,
        # or a single JSON object if stream=False.
        # For simplicity, we'll handle non-streamed responses first.
        # If stream=True, the response handling would need to iterate over response lines.
        if stream:
            # TODO: Implement proper streaming handling if needed.
            # For now, this example assumes stream=False for simplicity in return type.
            logger.warning("Streaming is not fully implemented in this client yet. Treating as non-streamed.")
            payload["stream"] = False # Override for now

        response_data = await self._make_request(self.api_generate_url, payload)
        return response_data # This will be a dict with 'response' key containing the generated text

    async def generate_embeddings(self, text_input: str) -> list[float]:
        """
        Generates embeddings for the given text input.
        """
        payload = {
            "model": self.model, # Ensure your model supports embeddings
            "prompt": text_input
        }
        response_data = await self._make_request(self.api_embeddings_url, payload)
        return response_data.get("embedding") # Returns a list of floats

    async def check_model_availability(self) -> bool:
        """
        Checks if the configured model is available in Ollama.
        (This is a conceptual check; Ollama's API might not have a direct "model exists" endpoint.
         A common way is to try a small request or list models if an endpoint exists for that.)
        For now, we can try listing models or just assume it's configured correctly.
        A more robust check would be to call /api/tags.
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                models = response.json().get("models", [])
                for model_info in models:
                    if model_info["name"].startswith(self.model): # e.g. granite:latest
                        logger.info(f"Model {self.model} is available on Ollama server.")
                        return True
                logger.warning(f"Model {self.model} not found in Ollama's list of available models.")
                return False
        except Exception as e:
            logger.error(f"Failed to check model availability or connect to Ollama: {e}")
            return False

# Example usage (for testing purposes, can be removed later)
if __name__ == "__main__":
    import asyncio

    async def main():
        # Ensure Ollama is running and the GRANITE_MODEL is pulled (e.g., ollama pull granite)
        # You might need to set OLLAMA_BASE_URL if it's not default
        
        print(f"Using Ollama base URL: {settings.OLLAMA_BASE_URL}")
        print(f"Using Granite model: {settings.GRANITE_MODEL}")

        service = OllamaService() # Will use defaults from settings
        
        model_available = await service.check_model_availability()
        print(f"Model '{service.model}' available: {model_available}")

        if model_available:
            try:
                # Test text generation
                # Simple prompt, no specific system instruction for this basic test
                text_response = await service.generate_text("Why is the sky blue?")
                print("\nGenerated Text:")
                print(text_response.get("response", "No response text found."))

                # Test embeddings generation
                embedding_response = await service.generate_embeddings("This is a test sentence for embeddings.")
                if embedding_response:
                    print(f"\nGenerated Embeddings (first 5 dimensions): {embedding_response[:5]}")
                    print(f"Total embedding dimensions: {len(embedding_response)}")
                else:
                    print("\nFailed to generate embeddings or model does not support it.")

            except Exception as e:
                print(f"An error occurred during API calls: {e}")
        else:
            print(f"Cannot proceed with tests as model '{service.model}' is not available or Ollama is unreachable.")

    # asyncio.run(main()) # Uncomment to run test
