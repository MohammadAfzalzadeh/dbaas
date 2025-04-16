FROM debian:bullseye-slim

ENV WALG_VERSION=v3.0.7

RUN apt-get update && apt-get install -y \
    gettext \
    bash \
    wget \
    ca-certificates \
    postgresql-client \
    tar \
    s3cmd   &&\
    wget https://github.com/wal-g/wal-g/releases/download/${WALG_VERSION}/wal-g-pg-ubuntu-20.04-amd64.tar.gz   &&\
    tar -zxvf wal-g-pg-ubuntu-20.04-amd64.tar.gz    &&\
    mv wal-g-pg-ubuntu-20.04-amd64 /usr/local/bin/wal-g &&\
    chmod +x /usr/local/bin/wal-g   &&\
    rm wal-g-pg-ubuntu-20.04-amd64.tar.gz   &&\
    apt-get clean && rm -rf /var/lib/apt/lists/*

# ENTRYPOINT ["/bin/bash"]
CMD [ "/bin/bash" , "-c" , "sleep 360000" ]