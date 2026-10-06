FROM node:18.20.8-bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev --ignore-scripts && npm cache clean --force
COPY pgcat-config-watcher.js pgcat-health.js logger.js ./
# UID changes require validation against the PgCat shared configuration volume.
CMD ["node", "pgcat-config-watcher.js"]
