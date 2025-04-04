# Use the official PostgreSQL image
FROM postgres:16

# Set environment variables
ENV POSTGRES_USER=user
ENV POSTGRES_PASSWORD=123
ENV REPLICA_TYPE=async

ENV MASTER_HOST=postgres_primary
ENV MASTER_PORT=5432
ENV REPLICATION_USER=replicator
ENV REPLICATION_PASS=123456


# Copy the initialization script into the container
COPY init-replica.sh /
COPY ./configs/ /etc/postgresql/

RUN chown -R postgres:postgres /etc/postgresql/ && \
    chmod -R 755 /etc/postgresql/ && \
    chmod 644 /etc/postgresql/*.conf && \
    chmod 644 /etc/postgresql/conf.d/* && \
    chmod +x /init-replica.sh &&\
    apt update && \
    apt install gettext -y && \
    envsubst < /etc/postgresql/conf.d/replica.conf.template > /etc/postgresql/conf.d/replica.conf


# Default command to run PostgreSQL in replication mode
USER postgres
CMD ["/bin/bash", "-c" , "/init-replica.sh ${REPLICA_TYPE}"]
