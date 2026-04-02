#!/bin/bash
# Run on the EC2 instance to deploy / update Red Forge.
# Usage: cd ~/red_forge && bash scripts/deploy.sh
set -e

APP_DIR="/home/ubuntu/red_forge"

echo "=== Red Forge Deploy ==="

# 1. Check .env exists
if [ ! -f "$APP_DIR/.env" ]; then
  echo "ERROR: $APP_DIR/.env not found."
  echo "Copy your .env file to the server first:"
  echo "  scp -i deploy3.pem .env ubuntu@32.192.255.100:/home/ubuntu/red_forge/.env"
  exit 1
fi

cd "$APP_DIR"

# 2. Prune old Docker resources to free disk on 20GB volume
echo "Pruning old Docker resources..."
docker system prune -af 2>/dev/null || true

# 3. Build and start all services
echo "Building containers (this may take a few minutes on t3.small)..."
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

# 4. Wait for API to be healthy
echo "Waiting for API to be ready..."
for i in {1..30}; do
  if curl -sf http://localhost/health > /dev/null 2>&1; then
    echo "API is up!"
    break
  fi
  echo "  attempt $i/30..."
  sleep 5
done

# 5. Show running containers
docker compose -f docker-compose.prod.yml ps

echo ""
echo "=== Deploy complete ==="
echo "Dashboard: http://32.192.255.100"
echo "API docs:  http://32.192.255.100/docs"
echo "Health:    http://32.192.255.100/health"
echo ""
echo "Logs: docker compose -f docker-compose.prod.yml logs -f"
