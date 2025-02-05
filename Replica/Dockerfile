# Use the official PostgreSQL image
FROM postgres:16

# Set environment variables
ENV POSTGRES_USER=user
ENV POSTGRES_PASSWORD=123
ENV PGUSER=replicator
ENV PGPASSWORD=123456
ENV REPLICA_TYPE=async


# Copy the initialization script into the container
COPY init-replica.sh /
COPY ./configs/ /etc/postgresql/

RUN chown -R postgres:postgres /etc/postgresql/ && \
    chmod -R 755 /etc/postgresql/ && \
    chmod 644 /etc/postgresql/*.conf && \
    chmod 644 /etc/postgresql/conf.d/* && \
    chmod +x /init-replica.sh

# Default command to run PostgreSQL in replication mode
USER postgres
CMD ["/bin/bash", "-c" , "/init-replica.sh ${REPLICA_TYPE}"]
