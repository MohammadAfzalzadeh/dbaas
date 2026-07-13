FROM docker.arvancloud.ir/node:18-slim

WORKDIR /app

COPY . .

RUN npm install --omit=dev


CMD ["node", "pgcat-config-watcher.js"]
