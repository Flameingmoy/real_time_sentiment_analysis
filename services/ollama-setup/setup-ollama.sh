#!/bin/sh
set -e

# Wait for the server to be ready
until ollama list > /dev/null 2>&1; do
  echo "Ollama server not yet running, waiting..."
  sleep 1
done

echo "Ollama server is running."

# Check if the model exists and pull if it doesn't
if ! ollama list | grep -q "$OLLAMA_MODEL"; then
  echo "Pulling model: $OLLAMA_MODEL"
  ollama pull "$OLLAMA_MODEL"
else
  echo "Model $OLLAMA_MODEL already exists."
fi