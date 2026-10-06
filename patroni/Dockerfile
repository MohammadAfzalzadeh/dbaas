FROM postgres:16.6-bookworm
COPY requirements.txt /tmp/patroni-requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-pip locales ca-certificates && \
    localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8 && \
    pip3 install --break-system-packages --no-cache-dir -r /tmp/patroni-requirements.txt && \
    mkdir -p /home/postgres && chown postgres:postgres /home/postgres && \
    sed -i 's|/var/lib/postgresql.*|/home/postgres:/bin/bash|' /etc/passwd && \
    chmod 775 /home/postgres && chmod 664 /etc/passwd && \
    rm -rf /var/lib/apt/lists/* /tmp/patroni-requirements.txt
COPY entrypoint.sh /
EXPOSE 5432 8008
ENV LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
# Patroni handles SIGTERM; the postgres base image declares SIGINT.
STOPSIGNAL SIGTERM
USER postgres
WORKDIR /home/postgres
CMD ["/bin/bash", "/entrypoint.sh"]
