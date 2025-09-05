# GigaChat Bootstrap Script for Windows
param(
    [switch]$UseDocker,
    [switch]$Yes,
    [switch]$Help
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# Script version
$VERSION = "1.0.0"

# Configuration
$PYTHON_VERSION = "3.8"
$REQUIRED_TOOLS = @("git", "python", "docker")
$VENV_PATH = ".venv"

function Write-Step {
    param($Message)
    Write-Host "`n🚀 $Message" -ForegroundColor Cyan
}

function Check-Command {
    param($Command)
    return [bool](Get-Command $Command -ErrorAction SilentlyContinue)
}

function Show-Help {
    Write-Host @"
GigaChat Development Environment Setup
Version: $VERSION

Usage:
    .\bootstrap.ps1 [options]

Options:
    -UseDocker     Use Docker for services (Redis, MinIO, etc.)
    -Yes           Non-interactive mode, assume yes for all prompts
    -Help          Show this help message

Requirements:
    - Git
    - Python $PYTHON_VERSION+
    - Docker (if using -UseDocker)
"@
    exit 0
}

if ($Help) { Show-Help }

# Check required tools
Write-Step "Checking required tools..."
foreach ($tool in $REQUIRED_TOOLS) {
    if (-not (Check-Command $tool)) {
        if ($tool -eq "docker" -and -not $UseDocker) {
            continue
        }
        Write-Host "❌ $tool is not installed" -ForegroundColor Red
        exit 1
    }
}

# Clone/pull repository if needed
Write-Step "Ensuring repository is up to date..."
if (-not (Test-Path ".git")) {
    git clone https://github.com/linkmeAman/gigaChat.git .
} else {
    git pull
}

# Create and activate virtual environment
Write-Step "Setting up Python virtual environment..."
if (-not (Test-Path $VENV_PATH)) {
    python -m venv $VENV_PATH
}
& ".\$VENV_PATH\Scripts\Activate.ps1"

# Install dependencies
Write-Step "Installing Python dependencies..."
python -m pip install --upgrade pip
if (Test-Path "requirements/dev.txt") {
    pip install -r requirements/dev.txt
} else {
    pip install -r requirements.txt
}

# Setup environment variables
Write-Step "Setting up environment variables..."
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env file from template. Please update with your settings."
}

# Start Docker services if requested
if ($UseDocker) {
    Write-Step "Starting Docker services..."
    docker-compose up -d redis minio
}

# Initialize database
Write-Step "Initializing database..."
alembic upgrade head

# Final instructions
Write-Step "Setup complete! 🎉"
Write-Host @"

To start development:
1. Update .env with your settings
2. Start the application:
   python app/main.py

For more information, see:
- README.md for project overview
- RUN.md for common commands and troubleshooting
"@