# Security Quick Start Guide

Quick reference for developers and operators working with the Product Issue Miner application.

---

## For Developers

### 1. Local Development Setup

```bash
# Copy environment template
cp backend/.env.example backend/.env

# Edit .env with your credentials
# Minimum required:
ZENDESK_SUBDOMAIN=workwelltech
ZENDESK_EMAIL=your-email@example.com
ZENDESK_API_TOKEN=your-token
ANTHROPIC_API_KEY=your-key
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/dbname
DASHBOARD_PASSWORD=dev-password-123  # Change this!

# Development-specific settings
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
ENVIRONMENT=development
LOG_LEVEL=DEBUG
```

### 2. Testing API with Authentication

```bash
# Without authentication (will fail)
curl http://localhost:8000/api/issues

# With authentication (will succeed)
curl -H "X-Dashboard-Password: dev-password-123" \
     http://localhost:8000/api/issues
```

### 3. Common Security Pitfalls to Avoid

❌ **DON'T**:
- Commit `.env` file to git
- Hard-code credentials in source code
- Use `CORS_ORIGINS=*` in production
- Disable security middleware for testing
- Log sensitive data (passwords, tokens)
- Use weak passwords for `DASHBOARD_PASSWORD`

✅ **DO**:
- Use environment variables for all credentials
- Keep `.env` in `.gitignore`
- Use strong, randomly generated passwords
- Test with authentication enabled
- Sanitize sensitive data before logging
- Use specific CORS origins

### 4. Security Testing

```bash
# Install security tools
pip install bandit safety

# Run security linter
bandit -r backend/app/

# Check for vulnerable dependencies
safety check --file backend/requirements.txt

# Test rate limiting (should return 429 on 6th request)
for i in {1..6}; do
  curl -H "X-Dashboard-Password: wrong" http://localhost:8000/api/issues
done
```

---

## For Operators

### 1. Production Environment Setup

```bash
# Generate strong password
DASHBOARD_PASSWORD=$(openssl rand -base64 32)

# Set production environment
ENVIRONMENT=production
LOG_LEVEL=INFO

# Configure CORS for your frontend domain
CORS_ORIGINS=https://dashboard.example.com

# Use secure database connection
DATABASE_URL=postgresql+asyncpg://user:strong_pass@db.example.com:5432/prod_db?ssl=require
```

### 2. Pre-Deployment Checklist

**Critical**:
- [ ] `DASHBOARD_PASSWORD` is strong (min 16 chars)
- [ ] `ENVIRONMENT=production`
- [ ] `CORS_ORIGINS` set to specific domains (NOT `*`)
- [ ] All credentials are production credentials
- [ ] Database uses SSL/TLS connection
- [ ] Secrets stored in secrets manager (not .env file)

**Important**:
- [ ] `LOG_LEVEL=INFO` or `WARNING`
- [ ] Rate limits configured appropriately
- [ ] HTTPS enabled with valid certificate
- [ ] Monitoring and alerting configured
- [ ] Backup strategy in place

### 3. Security Monitoring

**Daily**:
```bash
# Check authentication failures
grep "Invalid authentication" /var/log/app/*.log

# Check rate limit violations
grep "Rate limit exceeded" /var/log/app/*.log

# Review error logs
tail -100 /var/log/app/error.log
```

**Weekly**:
```bash
# Check for dependency vulnerabilities
safety check --file requirements.txt

# Review access patterns
# (Analyze logs for unusual activity)
```

### 4. Incident Response

**Authentication Failure Spike**:
```bash
# 1. Identify suspicious IPs
grep "Invalid authentication" /var/log/app/*.log | awk '{print $NF}' | sort | uniq -c

# 2. Block suspicious IPs at firewall/WAF
# 3. Rotate DASHBOARD_PASSWORD if needed
```

**API Abuse Detected**:
```bash
# 1. Identify abusive pattern
grep "Rate limit exceeded" /var/log/app/*.log

# 2. Temporarily increase rate limits or block IPs
# 3. Review and adjust rate limiting configuration
```

---

## Security Headers Reference

All responses include these security headers:

| Header | Value | Purpose |
|--------|-------|---------|
| X-Content-Type-Options | nosniff | Prevents MIME sniffing |
| X-Frame-Options | DENY | Prevents clickjacking |
| X-XSS-Protection | 1; mode=block | Browser XSS protection |
| Strict-Transport-Security | max-age=31536000 | Force HTTPS (prod) |
| Content-Security-Policy | restrictive | Resource loading control |
| Referrer-Policy | strict-origin-when-cross-origin | Referrer control |
| Permissions-Policy | restrictive | Feature control |

---

## Rate Limiting Reference

| Endpoint Type | Default Limit | Configurable Via |
|--------------|---------------|------------------|
| Authentication endpoints | 5 req/min | `AUTH_RATE_LIMIT` |
| General API endpoints | 100 req/min | `GENERAL_RATE_LIMIT` |
| Health check | No limit | N/A |

**Rate Limit Response**:
```json
HTTP/1.1 429 Too Many Requests
Retry-After: 60
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 0

{
  "detail": "Rate limit exceeded. Maximum 5 requests per minute."
}
```

---

## Authentication Reference

**Protected Endpoints**:
- All `/api/*` endpoints

**Public Endpoints**:
- `/` (root)
- `/health` (health check)
- `/docs` (API documentation)
- `/openapi.json` (OpenAPI spec)
- `/redoc` (ReDoc documentation)

**Authentication Method**:
```bash
# Include password in custom header
curl -H "X-Dashboard-Password: your-password-here" \
     https://api.example.com/api/issues
```

**Error Responses**:
- `401 Unauthorized`: Missing password
- `403 Forbidden`: Invalid password

---

## CORS Configuration

**Development**:
```bash
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
```

**Production**:
```bash
CORS_ORIGINS=https://dashboard.example.com,https://app.example.com
```

**Never use in production**:
```bash
CORS_ORIGINS=*  # ❌ Security risk!
```

---

## Common Issues & Solutions

### Issue: "Authentication required" error

**Cause**: Missing or incorrect `X-Dashboard-Password` header

**Solution**:
```bash
# Include password header in all API requests
curl -H "X-Dashboard-Password: your-password" \
     https://api.example.com/api/issues
```

### Issue: "Rate limit exceeded"

**Cause**: Too many requests from same IP

**Solution**:
- Wait 60 seconds before retrying
- Check `Retry-After` header
- Increase rate limits if legitimate traffic

### Issue: CORS error in browser

**Cause**: Frontend origin not in `CORS_ORIGINS`

**Solution**:
```bash
# Add frontend URL to CORS_ORIGINS
CORS_ORIGINS=https://dashboard.example.com,https://new-frontend.example.com
```

### Issue: "Request body too large"

**Cause**: Request exceeds `MAX_REQUEST_SIZE` (10MB default)

**Solution**:
```bash
# Increase limit if needed (in bytes)
MAX_REQUEST_SIZE=20971520  # 20MB
```

---

## Security Testing Checklist

### Before Committing Code

- [ ] No credentials in source code
- [ ] No debug prints with sensitive data
- [ ] Input validation on all new endpoints
- [ ] Error messages don't leak sensitive info
- [ ] Run `bandit -r backend/app/`

### Before Deployment

- [ ] Run security scans (`bandit`, `safety`)
- [ ] Review `DEPLOYMENT_SECURITY_CHECKLIST.md`
- [ ] Test authentication and rate limiting
- [ ] Verify security headers
- [ ] Test CORS configuration
- [ ] Review logs for sensitive data leakage

### After Deployment

- [ ] Verify HTTPS working
- [ ] Test authentication flow
- [ ] Monitor logs for errors
- [ ] Check security headers with curl
- [ ] Verify rate limiting working
- [ ] Test CORS from frontend

---

## Useful Commands

### Generate Strong Password
```bash
# 32-character random password
openssl rand -base64 32

# Or using Python
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Test Security Headers
```bash
curl -I https://api.example.com/health
```

### Test Authentication
```bash
# Should fail (401)
curl -v https://api.example.com/api/issues

# Should succeed (200)
curl -v -H "X-Dashboard-Password: password" \
     https://api.example.com/api/issues
```

### Test Rate Limiting
```bash
# Make 6 rapid requests (6th should be 429)
for i in {1..6}; do
  curl -H "X-Dashboard-Password: wrong" \
       https://api.example.com/api/issues
  echo ""
done
```

### Check SSL Certificate
```bash
openssl s_client -connect api.example.com:443 -servername api.example.com
```

### Monitor Logs in Real-time
```bash
# Application logs
tail -f /var/log/app/app.log

# Error logs only
tail -f /var/log/app/app.log | grep ERROR

# Security events
tail -f /var/log/app/app.log | grep -E "authentication|rate limit"
```

---

## Environment Variables Quick Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ZENDESK_SUBDOMAIN` | Yes | workwelltech | Zendesk subdomain |
| `ZENDESK_EMAIL` | Yes | - | Zendesk user email |
| `ZENDESK_API_TOKEN` | Yes | - | Zendesk API token |
| `ANTHROPIC_API_KEY` | Yes | - | Claude API key |
| `DATABASE_URL` | Yes | - | PostgreSQL connection URL |
| `DASHBOARD_PASSWORD` | Yes | - | API authentication password |
| `CORS_ORIGINS` | No | http://localhost:3000 | Allowed CORS origins |
| `AUTH_RATE_LIMIT` | No | 5 | Auth requests per minute |
| `GENERAL_RATE_LIMIT` | No | 100 | API requests per minute |
| `MAX_REQUEST_SIZE` | No | 10485760 | Max request size (bytes) |
| `ENVIRONMENT` | No | development | Environment name |
| `LOG_LEVEL` | No | INFO | Logging level |
| `REDIS_URL` | No | - | Redis connection URL |

---

## Emergency Contacts

**Security Issues**: [security@example.com]
**On-Call**: [phone/pager]
**Documentation**: See `SECURITY.md`

---

## Additional Documentation

For comprehensive security information, see:

- **SECURITY.md**: Complete security guide
- **SECURITY_AUDIT_REPORT.md**: Detailed audit report
- **DEPLOYMENT_SECURITY_CHECKLIST.md**: Deployment checklist
- **SECURITY_IMPROVEMENTS_SUMMARY.md**: Security enhancements summary

---

**Last Updated**: 2024-12-06
**Version**: 1.0
