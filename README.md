# GigaChat v1.3.0-free

[![Tests](https://github.com/linkmeAman/gigaChat/actions/workflows/tests.yml/badge.svg)](https://github.com/linkmeAman/gigaChat/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/linkmeAman/gigaChat/branch/master/graph/badge.svg)](https://codecov.io/gh/linkmeAman/gigaChat)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A powerful chat application with advanced features including AI integration, authentication, and multilingual support.

```
   ________  _______________  ________  ___  ____________
  / ____/  |/  / ____/ __ \/ ____/ / / /  |/  / ____/ /
 / / __/ /|_/ / __/ / /_/ / /   / /_/ / /|_/ / __/ / / 
/ /_/ / /  / / /___/ _, _/ /___/ __  / /  / / /___/_/  
\____/_/  /_/_____/_/ |_|\____/_/ /_/_/  /_/_____(_)   
```

## 📋 Table of Contents
1. [System Requirements](#system-requirements)
2. [Quick Start Guide](#quick-start-guide)
3. [Detailed Setup Instructions](#detailed-setup-instructions)
4. [Database Setup](#database-setup)
5. [Services Configuration](#services-configuration)
6. [Running the Application](#running-the-application)
7. [Monitoring & Observability](#monitoring--observability)
8. [Troubleshooting](#troubleshooting)

## 🔧 System Requirements

### Minimum Hardware Requirements
- CPU: 2 cores
- RAM: 4GB
- Storage: 20GB free space

### Software Requirements
- Python 3.8+
- MySQL 8.0+
- Docker & Docker Compose
- Git

## 🚀 Quick Start Guide

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd AmanChat
   ```

2. Create and activate virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Linux/Mac:
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. Start required services:
   ```bash
   docker-compose up -d redis minio
   ```

6. Initialize database:
   ```bash
   alembic upgrade head
   ```

7. Start the application:
   ```bash
   python app/main.py
   ```

## 📖 Detailed Setup Instructions

### Step 1: Environment Setup

1. **Python Virtual Environment**
   ```bash
   # Create virtual environment
   python -m venv venv
   
   # Activate it:
   # On Windows:
   venv\Scripts\activate
   # On Linux/Mac:
   source venv/bin/activate
   ```

2. **Dependencies Installation**
   ```bash
   # Install all required packages
   pip install -r requirements.txt
   ```

3. **Environment Configuration**
   - Copy `.env.example` to `.env`
   - Update the following variables:
     ```ini
     # Database Configuration
     DB_HOST=localhost
     DB_PORT=3306
     DB_USER=root
     DB_PASS=1234
     DB_NAME=gigachat

     # Redis Configuration
     REDIS_HOST=localhost
     REDIS_PORT=6379

     # MinIO Configuration
     MINIO_HOST=localhost
     MINIO_PORT=9000
     MINIO_ACCESS_KEY=minioadmin
     MINIO_SECRET_KEY=minioadmin
     ```

### Step 2: Database Setup

1. **MySQL Configuration**
   - Ensure MySQL is running
   - Create database:
     ```sql
     CREATE DATABASE gigachat;
     ```

2. **Run Migrations**
   ```bash
   # Initialize Alembic
   alembic init migrations

   # Run migrations
   alembic upgrade head
   ```

### Step 3: Service Configuration

1. **Redis Setup**
   ```bash
   # Start Redis container
   docker-compose up -d redis
   ```

2. **MinIO Setup**
   ```bash
   # Start MinIO container
   docker-compose up -d minio
   ```

3. **Monitoring Stack** (Optional)
   ```bash
   # Start monitoring services
   docker-compose -f docker-compose.observability.yml up -d
   ```

## 🎯 Running the Application

1. **Development Mode**
   ```bash
   python app/main.py
   ```

2. **Production Mode**
   ```bash
   docker-compose up -d
   ```

## 📊 Monitoring & Observability

Access monitoring tools at:
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090
- MinIO Console: http://localhost:9001

## ⚠️ Troubleshooting

### Common Issues and Solutions

1. **Database Connection Issues**
   - Verify MySQL is running
   - Check credentials in .env
   - Ensure database exists

2. **Redis Connection Errors**
   - Verify Redis container is running:
     ```bash
     docker ps | grep redis
     ```
   - Check Redis logs:
     ```bash
     docker logs redis
     ```

3. **Storage Issues**
   - Clear Docker volumes if needed:
     ```bash
     docker-compose down -v
     ```
   - Verify MinIO is accessible

### Memory Management

If you're running low on disk space:

1. **Clean Docker**
   ```bash
   # Remove unused containers
   docker container prune

   # Remove unused images
   docker image prune

   # Remove unused volumes
   docker volume prune
   ```

2. **Clean Python Cache**
   ```bash
   # Remove __pycache__ directories
   find . -type d -name __pycache__ -exec rm -r {} +
   ```

3. **Monitor Space Usage**
   ```bash
   # On Windows:
   dir /s
   # On Linux:
   du -h --max-depth=1
   ```

## 🔄 Branch Management

The project maintains two main branches:
- `master`: Production-ready code
- `aman`: Development branch

To switch branches:
```bash
# Switch to master
git checkout master

# Switch to aman
git checkout aman
```

## 📝 Development Workflow

1. Always work on the `aman` branch for new features
2. Create feature branches from `aman` if needed
3. Merge to `master` only when features are stable

---

For more information or support, please open an issue in the repository.

Remember to ⭐️ the repository if you find it helpful!