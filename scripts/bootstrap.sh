#!/usr/bin/env bash

# Exit on error
set -e

# Script version
VERSION="1.0.0"

# Configuration
PYTHON_VERSION="3.8"
REQUIRED_TOOLS=("git" "python3" "docker")
VENV_PATH=".venv"

# Colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Parse arguments
USE_DOCKER=0
YES=0

for arg in "$@"; do
  case $arg in
    --use-docker)
      USE_DOCKER=1
      shift
      ;;
    --yes)
      YES=1
      shift
      ;;
    --help)
      echo "GigaChat Development Environment Setup"
      echo "Version: $VERSION"
      echo
      echo "Usage:"
      echo "    ./bootstrap.sh [options]"
      echo
      echo "Options:"
      echo "    --use-docker    Use Docker for services (Redis, MinIO, etc.)"
      echo "    --yes          Non-interactive mode, assume yes for all prompts"
      echo "    --help         Show this help message"
      echo
      echo "Requirements:"
      echo "    - Git"
      echo "    - Python $PYTHON_VERSION+"
      echo "    - Docker (if using --use-docker)"
      exit 0
      ;;
  esac
done

# Helper functions
step() {
    echo -e "\n${CYAN}🚀 $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

# Check required tools
step "Checking required tools..."
for tool in "${REQUIRED_TOOLS[@]}"; do
    if [[ "$tool" == "docker" && $USE_DOCKER -eq 0 ]]; then
        continue
    fi
    if ! command -v $tool &> /dev/null; then
        error "$tool is not installed"
    fi
done

# Clone/pull repository if needed
step "Ensuring repository is up to date..."
if [ ! -d ".git" ]; then
    git clone https://github.com/linkmeAman/gigaChat.git .
else
    git pull
fi

# Create and activate virtual environment
step "Setting up Python virtual environment..."
if [ ! -d "$VENV_PATH" ]; then
    python3 -m venv $VENV_PATH
fi
source "$VENV_PATH/bin/activate"

# Install dependencies
step "Installing Python dependencies..."
python -m pip install --upgrade pip
if [ -f "requirements/dev.txt" ]; then
    pip install -r requirements/dev.txt
else
    pip install -r requirements.txt
fi

# Setup environment variables
step "Setting up environment variables..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "Created .env file from template. Please update with your settings."
fi

# Start Docker services if requested
if [ $USE_DOCKER -eq 1 ]; then
    step "Starting Docker services..."
    docker-compose up -d redis minio
fi

# Initialize database
step "Initializing database..."
alembic upgrade head

# Final instructions
step "Setup complete! 🎉"
echo -e """
To start development:
1. Update .env with your settings
2. Start the application:
   python app/main.py

For more information, see:
- README.md for project overview
- RUN.md for common commands and troubleshooting
"""