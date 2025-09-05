# Troubleshooting Guide

## Quick Reference

### Common Error Codes
| Code | Meaning | Quick Fix |
|------|----------|-----------|
| E001 | Database Connection | Check DATABASE_URL in .env |
| E002 | Redis Connection | Verify Redis is running |
| E003 | MinIO Access | Check MinIO credentials |
| E004 | Auth Failed | Verify PASETO_SECRET |
| E005 | AI Model Error | Check model settings |

### Health Check Commands
```bash
# API Health
curl http://localhost:8000/health

# Database
docker-compose exec db mysqladmin ping

# Redis
docker-compose exec redis redis-cli ping

# MinIO
curl http://localhost:9000/minio/health/live
```

## Component Troubleshooting

### 1. Database Issues

#### Connection Failures
```bash
# Check connection
docker-compose exec db mysql -u root -p -h localhost

# View logs
docker-compose logs db

# Common fixes:
1. Verify DATABASE_URL in .env
2. Check network connectivity
3. Confirm credentials
```

#### Performance Issues
```sql
-- Check slow queries
SHOW FULL PROCESSLIST;

-- Analyze table
ANALYZE TABLE your_table;

-- Check indexes
SHOW INDEX FROM your_table;
```

### 2. Redis Problems

#### Connection Refused
```bash
# Check Redis status
docker-compose ps redis

# View logs
docker-compose logs redis

# Common fixes:
1. Verify REDIS_URL in .env
2. Check Redis container is running
3. Confirm network settings
```

#### Memory Issues
```bash
# Check memory usage
docker-compose exec redis redis-cli info memory

# Clear cache if needed
docker-compose exec redis redis-cli FLUSHALL
```

### 3. AI Model Errors

#### Model Loading Failed
```python
# Check model settings in .env:
DEFAULT_MODEL=mistral-7b-instruct
MODEL_SERVER=vllm
DEVICE=cuda

# Verify GPU availability:
python -c "import torch; print(torch.cuda.is_available())"
```

#### Out of Memory
1. Reduce batch size
2. Switch to CPU mode
3. Use smaller model
4. Increase swap space

### 4. API Issues

#### High Latency
```bash
# Check response times
curl -w "Time: %{time_total}s" -o /dev/null -s "http://localhost:8000/health"

# Monitor requests
docker-compose logs -f api | grep "Processing time"
```

#### Rate Limiting
1. Check limits in config
2. Review Redis rate limiter
3. Adjust settings if needed

### 5. Authentication Problems

#### Token Invalid
1. Check PASETO_SECRET
2. Verify token expiration
3. Clear client cookies

#### Login Failed
1. Check password pepper
2. Verify user exists
3. Check account status

## Performance Optimization

### 1. Database Tuning
```sql
-- Optimize buffer pool
SET GLOBAL innodb_buffer_pool_size = 4G;

-- Optimize connections
SET GLOBAL max_connections = 1000;
```

### 2. Redis Optimization
```bash
# Edit redis.conf:
maxmemory 2gb
maxmemory-policy allkeys-lru
```

### 3. API Performance
```bash
# Uvicorn settings:
workers = 4
backlog = 2048
limit-concurrency = 1000
```

## Debugging Tools

### 1. Log Analysis
```bash
# Search errors
grep -r "ERROR" /var/log/gigachat/

# Track request
grep "request_id: xyz" /var/log/gigachat/
```

### 2. Performance Monitoring
```bash
# System resources
docker stats

# Network connections
netstat -tuln
```

### 3. Database Analysis
```sql
-- Show active connections
SHOW PROCESSLIST;

-- Table sizes
SELECT 
    table_name,
    table_rows,
    data_length/1024/1024 'Data MB',
    index_length/1024/1024 'Index MB'
FROM information_schema.tables
WHERE table_schema = 'gigachat';
```

## Recovery Procedures

### 1. Database Recovery
```bash
# Backup
mysqldump -u root -p gigachat > backup.sql

# Restore
mysql -u root -p gigachat < backup.sql
```

### 2. File Recovery
```bash
# MinIO backup
mc mirror minio/gigachat /backup/minio/

# Restore
mc mirror /backup/minio/ minio/gigachat
```

### 3. Complete Reset
```bash
# Stop services
docker-compose down -v

# Clean data
rm -rf data/*

# Rebuild
docker-compose up -d --build
```

## Preventive Maintenance

### 1. Regular Checks
- Monitor disk space
- Check error logs
- Review performance metrics
- Verify backups

### 2. Updates
```bash
# Update dependencies
pip install --upgrade -r requirements.txt

# Update Docker images
docker-compose pull
```

### 3. Security
```bash
# Run security checks
safety check
bandit -r .

# Update secrets regularly
# Rotate keys monthly
```