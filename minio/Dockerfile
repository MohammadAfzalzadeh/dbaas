FROM quay.io/minio/minio

# Copy entrypoint script
COPY entrypoint.sh /usr/bin/entrypoint.sh
RUN chmod +x /usr/bin/entrypoint.sh

# Set new entrypoint
ENTRYPOINT ["/usr/bin/entrypoint.sh"]
