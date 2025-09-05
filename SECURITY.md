# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.3.x   | :white_check_mark: |
| < 1.3   | :x:                |

## Security Controls

### Authentication & Authorization
- PASETO tokens for secure session management
- Password hashing with Bcrypt + pepper
- Rate limiting on auth endpoints
- Account lockout after failed attempts
- TOTP 2FA support
- CORS protection

### Data Protection
- All secrets use `SecretStr` type
- Encrypted storage with MinIO
- Input validation with Pydantic
- SQL injection protection via SQLAlchemy
- XSS protection via Content Security Policy
- HTTPS enforced in production

### API Security
- Rate limiting per endpoint
- Request size limits
- Authentication timeout
- API versioning
- Input sanitization

### Infrastructure
- Container security scanning
- Dependencies security scanning
- Regular security updates
- Automated vulnerability checks
- Secure configuration defaults

## Development Security Requirements

1. **Environment Variables**
   - Never commit `.env` files
   - Use `.env.example` as template
   - Use strong random values in production

2. **Dependencies**
   - Pin all dependency versions
   - Regular security updates
   - Automated vulnerability scanning

3. **Code Quality**
   - Pre-commit hooks enabled
   - Security linting with Bandit
   - Type checking with MyPy
   - Regular dependency updates

4. **Access Control**
   - Principle of least privilege
   - Role-based access control
   - Resource-level permissions

## Reporting a Vulnerability

1. **Do Not** create a public issue
2. Email security@yourdomain.com
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We aim to respond within 48 hours and fix critical issues within 7 days.

## Security Checklist for Deployment

1. **Pre-deployment**
   - [ ] Security scan passed
   - [ ] Dependencies updated
   - [ ] Secrets rotated
   - [ ] Permissions reviewed

2. **Configuration**
   - [ ] Debug mode disabled
   - [ ] Secure headers enabled
   - [ ] Rate limits configured
   - [ ] Logging enabled

3. **Infrastructure**
   - [ ] Firewall configured
   - [ ] TLS enabled
   - [ ] Backup system ready
   - [ ] Monitoring active

4. **Post-deployment**
   - [ ] Security headers verified
   - [ ] Rate limits tested
   - [ ] Logging confirmed
   - [ ] Monitoring alerts tested