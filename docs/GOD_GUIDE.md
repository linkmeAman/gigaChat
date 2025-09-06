# GOD Guide - GitHub CI/CD Ultimate Reference

## 1. GitHub Actions Essentials

### 1.1 Core Concepts
- **Workflow**: `.github/workflows/*.yml` files
- **Event**: What triggers the workflow
- **Job**: Collection of steps
- **Step**: Individual task
- **Action**: Reusable unit
- **Runner**: Server running the workflow

### 1.2 Best Practices
1. **Version Control**
   ```yaml
   # BAD ❌
   uses: actions/checkout@v4
   
   # GOOD ✅
   uses: actions/checkout@8ade135a41bc03ea155e62e844d188df1ea18608  # v4.1.0
   ```

2. **Permissions**
   ```yaml
   # GOOD ✅
   permissions:
     contents: read
     checks: write
   ```

3. **Concurrency**
   ```yaml
   concurrency:
     group: ${{ github.workflow }}-${{ github.ref }}
     cancel-in-progress: true
   ```

4. **Caching**
   ```yaml
   - uses: actions/setup-python@v4
     with:
       cache: pip
       cache-dependency-path: |
         requirements.txt
         requirements-dev.txt
   ```

## 2. Python Testing Setup

### 2.1 Essential Files
- `requirements.txt`: Production dependencies
- `requirements-dev.txt`: Development dependencies
- `pytest.ini`: PyTest configuration
- `.coveragerc`: Coverage settings

### 2.2 Running Tests
```yaml
- name: Run Tests
  env:
    PYTHONPATH: .
    DATABASE_URL: sqlite:///./test.db
  run: |
    pytest --cov=app --cov-report=xml
```

### 2.3 Coverage Best Practices
1. Set threshold in workflow:
   ```yaml
   - name: Check Coverage
     run: coverage report --fail-under=80
   ```

2. Upload reports:
   ```yaml
   - uses: actions/upload-artifact@v4
     with:
       name: coverage-report
       path: htmlcov/
   ```

## 3. Environment & Secrets

### 3.1 Environment Files
- `.env`: Production settings
- `.env.test`: Test settings
- `.env.example`: Template (commit this)

### 3.2 GitHub Secrets
- Access: `${{ secrets.SECRET_NAME }}`
- Set via: Settings → Secrets → Actions
- Never log or print secrets

## 4. Database Setup

### 4.1 SQLite for Tests
```yaml
env:
  DATABASE_URL: sqlite:///./test.db
```

### 4.2 Migration Handling
```yaml
steps:
  - name: Run Migrations
    run: |
      alembic upgrade head
```

## 5. Troubleshooting

### 5.1 Common Issues
1. **Permission Denied**
   - Check workflow permissions
   - Verify token scopes
   - Check file permissions

2. **Cache Miss**
   - Verify cache key
   - Check dependency files
   - Clear cache if needed

3. **Test Failures**
   - Check environment variables
   - Verify database setup
   - Review coverage settings

### 5.2 Debugging Tips
1. Enable debug logging:
   ```yaml
   env:
     ACTIONS_RUNNER_DEBUG: true
   ```

2. Use step debugging:
   ```yaml
   steps:
     - name: Debug
       run: |
         env
         pwd
         ls -la
   ```

## 6. Maintenance

### 6.1 Regular Updates
1. Check for action updates monthly
2. Update Python versions yearly
3. Review dependencies quarterly
4. Audit permissions bi-annually

### 6.2 Security
1. Use dependabot
2. Pin action versions
3. Limit permissions
4. Scan secrets
5. Review logs

## 7. References
- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [PyTest Docs](https://docs.pytest.org/)
- [Coverage.py Docs](https://coverage.readthedocs.io/)
- [GitHub Security Best Practices](https://docs.github.com/en/actions/security-guides)