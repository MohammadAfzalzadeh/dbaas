# Use the official PostgreSQL image as the base
FROM postgres:16

# Set environment variables (can also be passed during container runtime)
ENV POSTGRES_USER=user
ENV POSTGRES_DB=postgres
ENV POSTGRES_PASSWORD=123
# ENV POSTGRES_HOST_AUTH_METHOD="scram-sha-256\nhost replication replicator 0.0.0.0/0 md5"
ENV POSTGRES_INITDB_ARGS="--auth-host=scram-sha-256"
ENV POSTGRES_REPLICA_SYNC="sync"

# Copy any initialization scripts (SQL) to the Docker entrypoint directory
COPY ./00_init.sql /docker-entrypoint-initdb.d/00_init.sql
COPY ./configs/ /etc/postgresql/

RUN chown -R postgres:postgres /etc/postgresql/ && \
    chmod -R 755 /etc/postgresql/ && \
    chmod 644 /etc/postgresql/*.conf && \
    chmod 644 /etc/postgresql/conf.d/*

# Add the healthcheck
# HEALTHCHECK --interval=10s --timeout=5s --retries=5 CMD pg_isready -U user --dbname=postgres || exit 1

EXPOSE 5432
# Configure the PostgreSQL server with the required settings
CMD ["postgres" , "-c" , "config_file=/etc/postgresql/postgresql.conf"]