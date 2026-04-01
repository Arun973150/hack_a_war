# Run this from YOUR Windows machine to upload the project to EC2.
# Usage: .\upload-to-ec2.ps1 -KeyFile "C:\path\to\key.pem" -EC2IP "1.2.3.4"

param(
    [Parameter(Mandatory=$true)]
    [string]$KeyFile,

    [Parameter(Mandatory=$true)]
    [string]$EC2IP
)

$ProjectDir = "C:\Users\ADMIN\OneDrive\Desktop\red_forge"
$RemoteUser = "ubuntu"
$RemotePath = "/home/ubuntu/red_forge"

Write-Host "=== Uploading Red Forge to EC2 (clean) ===" -ForegroundColor Green
Write-Host "Target: ${RemoteUser}@${EC2IP}:${RemotePath}"

# Create remote directory structure
Write-Host "`nCreating remote directories..." -ForegroundColor Cyan
ssh -i $KeyFile -o StrictHostKeyChecking=no "${RemoteUser}@${EC2IP}" "mkdir -p $RemotePath/dashboard"

# ── Upload backend & infra files (no heavy dirs) ─────────────────────────────
Write-Host "`nUploading backend code..." -ForegroundColor Cyan

# These directories are small and safe to upload entirely
$smallDirs = @("api", "agents", "ingestion", "knowledge", "monitoring", "org_context", "storage", "docker", "nginx", "scripts")

foreach ($dir in $smallDirs) {
    $localPath = "$ProjectDir\$dir"
    if (Test-Path $localPath) {
        Write-Host "  -> $dir/"
        scp -i $KeyFile -r "$localPath" "${RemoteUser}@${EC2IP}:${RemotePath}/"
    }
}

# ── Upload individual config files ───────────────────────────────────────────
Write-Host "`nUploading config files..." -ForegroundColor Cyan
$configFiles = @(
    "config.py",
    "pyproject.toml",
    "docker-compose.prod.yml",
    "docker-compose.yml",
    "redforge-13436394829f.json",
    ".env"
)

foreach ($file in $configFiles) {
    $localPath = "$ProjectDir\$file"
    if (Test-Path $localPath) {
        Write-Host "  -> $file"
        scp -i $KeyFile "$localPath" "${RemoteUser}@${EC2IP}:${RemotePath}/"
    }
}

# ── Upload dashboard source ONLY (no node_modules, no .next) ─────────────────
Write-Host "`nUploading dashboard source (excluding node_modules & .next)..." -ForegroundColor Cyan

# Upload dashboard config files
$dashboardFiles = @(
    "package.json",
    "package-lock.json",
    "next.config.js",
    "tsconfig.json",
    "tailwind.config.ts",
    "postcss.config.js",
    "next-env.d.ts"
)

foreach ($file in $dashboardFiles) {
    $localPath = "$ProjectDir\dashboard\$file"
    if (Test-Path $localPath) {
        Write-Host "  -> dashboard/$file"
        scp -i $KeyFile "$localPath" "${RemoteUser}@${EC2IP}:${RemotePath}/dashboard/"
    }
}

# Upload dashboard/src directory (the actual source code)
if (Test-Path "$ProjectDir\dashboard\src") {
    Write-Host "  -> dashboard/src/"
    scp -i $KeyFile -r "$ProjectDir\dashboard\src" "${RemoteUser}@${EC2IP}:${RemotePath}/dashboard/"
}

# Upload dashboard/public directory if it exists
if (Test-Path "$ProjectDir\dashboard\public") {
    Write-Host "  -> dashboard/public/"
    scp -i $KeyFile -r "$ProjectDir\dashboard\public" "${RemoteUser}@${EC2IP}:${RemotePath}/dashboard/"
}

# Upload dashboard/.env.local if it exists
if (Test-Path "$ProjectDir\dashboard\.env.local") {
    Write-Host "  -> dashboard/.env.local"
    scp -i $KeyFile "$ProjectDir\dashboard\.env.local" "${RemoteUser}@${EC2IP}:${RemotePath}/dashboard/"
}

Write-Host ""
Write-Host "=== Upload complete ===" -ForegroundColor Green
Write-Host "Now SSH into your server and run:"
Write-Host "  ssh -i $KeyFile ${RemoteUser}@${EC2IP}"
Write-Host "  bash /home/ubuntu/red_forge/scripts/setup-ec2.sh   # first time only"
Write-Host "  bash /home/ubuntu/red_forge/scripts/deploy.sh"
