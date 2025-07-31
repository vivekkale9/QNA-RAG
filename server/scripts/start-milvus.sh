#!/bin/bash

# Start Milvus with persistent storage
# This script sets up Milvus with Docker volumes for data persistence

echo "🚀 Starting Milvus with persistent storage..."

# Docker will automatically create named volumes for persistence
# No need to create directories manually with named volumes

# Start Milvus services
docker-compose up -d

echo "⏳ Waiting for Milvus to be ready..."
sleep 30

# Check if Milvus is running
if curl -f http://localhost:9091/healthz > /dev/null 2>&1; then
    echo "✅ Milvus is running successfully!"
    echo "📊 Milvus UI (Attu): http://localhost:3000"
    echo "🔌 Milvus API: localhost:19530"
    echo "🗄️ MinIO Console: http://localhost:9001"
    echo "💾 Data is persisted in Docker named volumes"
else
    echo "❌ Milvus failed to start. Check logs with: docker-compose logs"
    exit 1
fi 