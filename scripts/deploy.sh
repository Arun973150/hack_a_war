#!/bin/bash
# Run on the EC2 instance to deploy / update Red Forge.
# Usage: bash deploy.sh
set -e

APP_DIR="/home/ubuntu/red_forge"

echo "=== Red Forge Deploy ==="

# 1. Check .env exists
if [ ! -f "$APP_DIR/.env" ]; then
  echo "ERROR: $APP_DIR/.env not found."
  echo "Copy your .env file to the server first:"
  echo "  scp -i key.pem .env ubuntu@<EC2-IP>:/home/ubuntu/red_forge/.env"
  exit 1
fi

cd "$APP_DIR"

# 2. Pull latest (if using git)
if [ -d ".git" ]; then
  git pull origin main
fi

# 3. Build and start all services
docker compose -f docker-compose.prod.yml build --no-cache
docker compose -f docker-compose.prod.yml up -d

# 4. Wait for API to be healthy
echo "Waiting for API to be ready..."
for i in {1..20}; do
  if curl -sf http://localhost/health > /dev/null 2>&1; then
    echo "API is up!"
    break
  fi
  echo "  attempt $i/20..."
  sleep 5
done

# 5. Show running containers
docker compose -f docker-compose.prod.yml ps

echo ""
echo "=== Deploy complete ==="
echo "Frontend: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)/demo"
echo "API docs: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)/docs"
echo "Health:   http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)/health"
