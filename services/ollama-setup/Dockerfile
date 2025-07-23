FROM ollama/ollama:latest

COPY setup-ollama.sh /usr/local/bin/setup-ollama.sh
RUN chmod +x /usr/local/bin/setup-ollama.sh

ENTRYPOINT ["setup-ollama.sh"]