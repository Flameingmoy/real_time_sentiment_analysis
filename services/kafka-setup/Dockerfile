FROM confluentinc/cp-kafka:7.4.0

COPY setup-kafka.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/setup-kafka.sh

CMD ["setup-kafka.sh"]
