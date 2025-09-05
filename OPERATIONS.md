# Operations Guide

## Deployment

### Prerequisites
- Docker & Docker Compose
- Python 3.8+
- MySQL 8.0+
- 4GB+ RAM
- 20GB+ storage

### Production Setup

1. **Clone Repository**
```bash
git clone https://github.com/linkmeAman/gigaChat.git
cd gigaChat
```

2. **Environment Setup**
```bash
# Copy and edit environment variables
cp .env.example .env
# Generate secure values for:
# - PASETO_SECRET
# - AUTH_PASSWORD_PEPPER
# - MINIO_ACCESS_KEY
# - MINIO_SECRET_KEY
```

3. **Start Services**
```bash
# Start all services
docker-compose up -d

# Verify services
docker-compose ps
```

4. **Database Setup**
```bash
# Run migrations
alembic upgrade head

# Verify database
docker-compose exec db mysql -u root -p gigachat -e "SHOW TABLES;"
```

5. **Health Checks**
```bash
# Check API health
curl http://localhost:8000/health

# Check Redis
docker-compose exec redis redis-cli ping

# Check MinIO
curl http://localhost:9000/minio/health/live
```

## Monitoring

### Metrics
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090
- Alert Manager: http://localhost:9093

### Logging
- Location: /var/log/gigachat/
- Format: JSON
- Rotation: Daily
- Retention: 7 days

### Alerts
1. High Error Rate
2. API Latency
3. Database Connections
4. Cache Hit Rate
5. Disk Space
6. Memory Usage

## Backup & Recovery

### Database Backup
```bash
# Daily backup
0 0 * * * docker-compose exec db mysqldump -u root -p gigachat > backup.sql

# Restore
cat backup.sql | docker-compose exec -T db mysql -u root -p gigachat
```

### File Storage Backup
```bash
# Backup MinIO
mc mirror minio/gigachat /backup/minio/

# Restore MinIO
mc mirror /backup/minio/ minio/gigachat
```

## Scaling

### Horizontal Scaling
```bash
# Scale API servers
docker-compose up -d --scale api=3

# Scale workers
docker-compose up -d --scale worker=5
```

### Performance Tuning
1. Database
```sql
-- Optimize connections
SET GLOBAL max_connections = 1000;
SET GLOBAL innodb_buffer_pool_size = 4G;
```

2. Redis
```bash
# Edit redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
```

3. Application
```bash
# Edit uvicorn settings
--workers 4
--backlog 2048
--limit-concurrency 1000
```

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
```bash
# Check connectivity
docker-compose exec db mysql -u root -p -h localhost

# Check logs
docker-compose logs db
```

2. **Redis Issues**
```bash
# Check memory
docker-compose exec redis redis-cli info memory

# Clear cache
docker-compose exec redis redis-cli FLUSHALL
```

3. **API Performance**
```bash
# Check response times
curl -w "@curl-format.txt" -o /dev/null -s "http://localhost:8000/health"

# Profile endpoints
docker-compose logs api | grep "Processing time"
```

### Debug Tools

1. **Log Analysis**
```bash
# Search errors
grep -r "ERROR" /var/log/gigachat/

# Track request
grep "request_id: xyz" /var/log/gigachat/
```

2. **Performance Analysis**
```bash
# CPU/Memory usage
docker stats

# Network connections
netstat -tuln
```

3. **Disk Space**
```bash
# Check usage
df -h

# Find large files
find /var/log -type f -size +100M
```

## Maintenance

### Regular Tasks

1. **Daily**
- Check error logs
- Verify backups
- Monitor disk space
- Review active users

2. **Weekly**
- Review performance metrics
- Check security updates
- Analyze slow queries
- Verify data retention

3. **Monthly**
- Rotate credentials
- Update dependencies
- Review access logs
- Test recovery procedures

### Security Updates
```bash
# Update base images
docker-compose pull

# Update Python packages
pip install --upgrade -r requirements.txt

# Rebuild containers
docker-compose up -d --build
```

## Disaster Recovery

### Recovery Steps

1. **Service Failure**
```bash
# Restart service
docker-compose restart service_name

# Check logs
docker-compose logs --tail=100 service_name
```

2. **Data Corruption**
```bash
# Stop services
docker-compose down

# Restore database
mysql gigachat < backup.sql

# Restore files
mc mirror /backup/minio/ minio/gigachat
```

3. **Complete Recovery**
```bash
# Fresh installation
git clone https://github.com/linkmeAman/gigaChat.git
# Follow setup steps
# Restore data
```

## Compliance & Auditing

### Audit Logs
- User actions
- System changes
- Access attempts
- Data modifications

### Compliance Checks
```bash
# Security scan
safety check
bandit -r .

# Dependency audit
pip-audit

# Code quality
black --check .
mypy .
```