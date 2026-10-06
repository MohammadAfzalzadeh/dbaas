FROM golang:1.24.2-bookworm AS builder
ARG MINIO_VERSION=RELEASE.2025-04-22T22-12-26Z
ARG MINIO_SHA256=1a63209927b9d1fb239b2a776b7b01d1902eff19379a108f4bc7005edcc0968c
WORKDIR /src
RUN curl -fsSL "https://codeload.github.com/minio/minio/tar.gz/refs/tags/${MINIO_VERSION}" -o source.tar.gz && \
    echo "${MINIO_SHA256}  source.tar.gz" | sha256sum -c - && \
    tar xzf source.tar.gz --strip-components=1 && rm source.tar.gz && \
    CGO_ENABLED=0 go build -mod=readonly -trimpath -o /minio .
FROM debian:12.9-slim
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/*
COPY --from=builder /minio /usr/local/bin/minio
EXPOSE 9000 9001
ENTRYPOINT ["minio"]
