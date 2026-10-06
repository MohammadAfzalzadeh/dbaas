FROM golang:1.24.2-bookworm AS builder
ARG MC_VERSION=RELEASE.2025-04-16T18-13-26Z
ARG MC_SHA256=526ec538e7f83e4bfa631788129b08ec85898ca572ce0523ebf9a597946bea27
WORKDIR /src
RUN curl -fsSL "https://codeload.github.com/minio/mc/tar.gz/refs/tags/${MC_VERSION}" -o source.tar.gz && \
    echo "${MC_SHA256}  source.tar.gz" | sha256sum -c - && \
    tar xzf source.tar.gz --strip-components=1 && rm source.tar.gz && \
    CGO_ENABLED=0 go build -mod=readonly -trimpath -o /mc .
FROM debian:12.9-slim
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/*
COPY --from=builder /mc /usr/local/bin/mc
ENTRYPOINT ["mc"]
