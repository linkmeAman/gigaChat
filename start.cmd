@echo off
echo Starting GigaChat v1.3.0-free...

REM Check if Docker is running
docker info > nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Docker is not running. Please start Docker Desktop.
    exit /b 1
)

REM Create necessary directories
mkdir config\grafana\dashboards 2> nul
mkdir app\i18n 2> nul
mkdir app\uploads 2> nul
mkdir exports 2> nul

REM Build and start observability stack
echo Starting observability services...
docker-compose -f docker-compose.observability.yml up -d

REM Wait for services to be ready
timeout /t 10 /nobreak

REM Build and start main application
echo Starting GigaChat services...
docker-compose up -d

echo.
echo GigaChat is starting up! Please wait...
echo.
echo Services will be available at:
echo - Main Application: http://localhost:8000
echo - Grafana Dashboard: http://localhost:3000
echo - Prometheus: http://localhost:9090
echo - MinIO Console: http://localhost:9001
echo.
echo Default credentials:
echo - Grafana: admin/admin
echo - MinIO: minioadmin/minioadmin
echo.
echo Press Ctrl+C to view logs or use 'docker-compose logs -f' to monitor the services.