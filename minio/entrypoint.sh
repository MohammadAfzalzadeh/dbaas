#!/bin/bash

# Start MinIO server in the background
minio server /data --console-address ":9090" &
sleep 5

# Define credentials and bucket
MINIO_ACCESS_KEY="pgbackup-access-key"
MINIO_SECRET_KEY="pgbackup-secret-key"
BUCKET_NAME="pgbackup"

# Use MinIO Client (`mc`) to configure MinIO
mc alias set myminio http://localhost:9000 admin admin123
#create bucket
mc mb myminio/$BUCKET_NAME

# Keep container running
wait
