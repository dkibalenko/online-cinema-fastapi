#!/bin/sh

echo "Waiting for MinIO to be ready..."
sleep 5

echo "Configuring MinIO Client..."
mc alias set minio http://"$S3_STORAGE_HOST":"$S3_STORAGE_PORT" "$S3_STORAGE_ACCESS_KEY" "$S3_STORAGE_SECRET_KEY"

if mc ls minio | grep -q "$S3_BUCKET_NAME"; then
    echo "Bucket '$S3_BUCKET_NAME' already exists. Skipping creation."
else
    echo "Creating bucket: $S3_BUCKET_NAME"
    mc mb minio/"$S3_BUCKET_NAME"
fi

echo "Setting bucket policy to public..."
mc anonymous set download minio/"$S3_BUCKET_NAME"

echo "Getting policy info..."
mc anonymous get minio/"$S3_BUCKET_NAME"

echo "MinIO configuration completed!"
exit 0
