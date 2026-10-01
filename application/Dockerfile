FROM python:3.12-slim

# install helm + kubectl (as root)
RUN apt-get update && apt-get install -y curl ca-certificates gnupg && \
    curl -sSL https://get.helm.sh/helm-v3.15.4-linux-amd64.tar.gz | tar zx && \
    mv linux-amd64/helm /usr/local/bin/helm && rm -rf linux-amd64 && \
    curl -sSL -o /usr/local/bin/kubectl https://storage.googleapis.com/kubernetes-release/release/v1.30.0/bin/linux/amd64/kubectl && \
    chmod +x /usr/local/bin/kubectl && \
    apt-get purge -y curl gnupg && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

# app dir
WORKDIR /app
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy code & charts
COPY app/ ./app/
COPY static/ ./static/
COPY helmCharts/ ./helmCharts/

# --- create non-root user and give it ownership ---
# use a stable UID/GID (10001) so you can set runAsUser later
RUN groupadd -g 10001 app && useradd -u 10001 -g 10001 -m -d /home/app app && \
    chown -R app:app /app /home/app

# helm likes a writable HOME; set XDG dirs to prevent permission issues
ENV HOME=/home/app \
    HELM_CACHE_HOME=/home/app/.cache/helm \
    HELM_CONFIG_HOME=/home/app/.config/helm \
    HELM_DATA_HOME=/home/app/.local/share/helm
RUN mkdir -p $HELM_CACHE_HOME $HELM_CONFIG_HOME $HELM_DATA_HOME && chown -R app:app /home/app

USER 10001:10001

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host=0.0.0.0", "--port=8000"]
