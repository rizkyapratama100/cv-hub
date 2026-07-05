#!/usr/bin/env bash
# deploy.sh — run this on the Lightsail instance to deploy/update the backend
# Usage: bash deploy.sh

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Pulling latest changes..."
git -C "$REPO_DIR" pull

echo "==> Building Docker image..."
docker compose -f "$REPO_DIR/docker-compose.prod.yml" build --no-cache

echo "==> Stopping existing container..."
docker compose -f "$REPO_DIR/docker-compose.prod.yml" down

echo "==> Starting updated container..."
docker compose -f "$REPO_DIR/docker-compose.prod.yml" up -d

echo "==> Waiting for health check..."
sleep 4
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/health)
if [ "$STATUS" = "200" ]; then
  echo "✓ Backend healthy (HTTP $STATUS)"
else
  echo "✗ Health check failed (HTTP $STATUS) — check logs:"
  docker compose -f "$REPO_DIR/docker-compose.prod.yml" logs --tail=30
  exit 1
fi

echo "==> Cleaning up unused Docker images..."
docker image prune -f

echo "✓ Deployment complete."
