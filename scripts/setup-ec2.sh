#!/bin/bash
# Run this ONCE on a fresh Ubuntu 22.04 EC2 instance (t3.small, 2GB RAM).
# Usage: bash setup-ec2.sh
set -e

echo "=== Red Forge EC2 Setup ==="

# 1. System updates
sudo apt-get update -y
sudo apt-get upgrade -y
sudo apt-get install -y git curl unzip

# 2. Add 4GB swap (t3.small has 2GB RAM — Docker builds will OOM without this)
if [ ! -f /swapfile ]; then
  echo "Creating 4GB swap..."
  sudo fallocate -l 4G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
fi

# 3. Install Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER

# 4. Install Docker Compose v2
sudo apt-get install -y docker-compose-plugin
docker compose version

# 5. Firewall — allow HTTP, HTTPS, SSH
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8000/tcp
sudo ufw --force enable

# 6. Clean up disk space
sudo apt-get autoremove -y
sudo apt-get clean

echo ""
echo "=== Setup complete ==="
echo "Log out and log back in for docker group to take effect:"
echo "  exit"
echo "  ssh -i deploy3.pem ubuntu@32.192.255.100"
echo "Then run: cd ~/red_forge && bash scripts/deploy.sh"
