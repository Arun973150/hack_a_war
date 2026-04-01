#!/bin/bash
# Run this ONCE on a fresh Ubuntu 22.04 EC2 instance.
# Usage: bash setup-ec2.sh
set -e

echo "=== Red Forge EC2 Setup ==="

# 1. System updates
sudo apt-get update -y
sudo apt-get upgrade -y
sudo apt-get install -y git curl unzip python3-pip

# 2. Install Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER

# 3. Install Docker Compose v2
sudo apt-get install -y docker-compose-plugin
docker compose version

# 4. Install AWS CLI (optional, for pulling from ECR later)
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "/tmp/awscliv2.zip"
unzip /tmp/awscliv2.zip -d /tmp
sudo /tmp/aws/install
rm -rf /tmp/aws /tmp/awscliv2.zip

# 5. Firewall — allow HTTP, HTTPS, SSH only
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

echo ""
echo "=== Setup complete ==="
echo "Log out and log back in for docker group to take effect."
echo "Then run: bash deploy.sh"
