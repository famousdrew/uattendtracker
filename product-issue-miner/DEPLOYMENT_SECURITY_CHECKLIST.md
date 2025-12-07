# Deployment Security Checklist

Quick reference checklist for secure deployment of Product Issue Miner.

---

## Pre-Deployment Security Checklist

### 1. Environment Configuration

#### Required Environment Variables
- [ ] `ZENDESK_SUBDOMAIN` set correctly
- [ ] `ZENDESK_EMAIL` configured
- [ ] `ZENDESK_API_TOKEN` is production token (not test)
- [ ] `ANTHROPIC_API_KEY` is production key
- [ ] `DATABASE_URL` uses secure credentials
- [ ] `DASHBOARD_PASSWORD` is strong (min 16 chars, random)
- [ ] `ENVIRONMENT` set to `production`
- [ ] `LOG_LEVEL` set to `INFO` or `WARNING`

#### CORS Configuration
- [ ] `CORS_ORIGINS` set to specific domains (NOT `*`)
- [ ] All allowed origins are HTTPS in production
- [ ] No development URLs in production CORS list

#### Rate Limiting
- [ ] `AUTH_RATE_LIMIT` configured (default: 5)
- [ ] `GENERAL_RATE_LIMIT` tuned for expected usage
- [ ] Consider Redis for distributed rate limiting

### 2. Secrets Management

#### Development
- [ ] `.env` file exists and is in `.gitignore`
- [ ] No credentials in source code
- [ ] `.env.example` has no real values

#### Production
- [ ] Using secrets manager (AWS Secrets Manager, Vault, etc.)
- [ ] Database credentials are strong and unique
- [ ] Redis password configured (if using Redis)
- [ ] API keys are production keys
- [ ] Secrets are encrypted at rest

### 3. Database Security

- [ ] Database uses SSL/TLS connections
- [ ] Database password is strong (20+ characters)
- [ ] Database accessible only from application servers
- [ ] Database backups configured and tested
- [ ] Connection pooling configured
- [ ] Database user has minimal necessary permissions

Example secure connection:
```bash
DATABASE_URL=postgresql+asyncpg://user:strong_pass@db.example.com:5432/prod_db?ssl=require
```

### 4. Network Security

#### HTTPS/TLS
- [ ] Application runs behind HTTPS (production)
- [ ] Valid SSL/TLS certificate installed
- [ ] HTTP redirects to HTTPS
- [ ] HSTS header enabled (via `ENVIRONMENT=production`)
- [ ] TLS 1.2+ only (disable older protocols)

#### Firewall Rules
- [ ] API accessible only from frontend domains
- [ ] Database accessible only from application servers
- [ ] Redis accessible only from application servers
- [ ] SSH/RDP restricted to admin IPs

#### Reverse Proxy (Nginx/Apache)
- [ ] Reverse proxy configured
- [ ] Security headers set at proxy level
- [ ] Rate limiting at proxy level (optional)
- [ ] DDoS protection enabled

### 5. Application Security

#### Dependencies
- [ ] All dependencies up to date
- [ ] No critical security vulnerabilities (`safety check`)
- [ ] Dependency scanning in CI/CD pipeline
- [ ] SBOM generated (optional)

#### Security Middleware
- [ ] Security headers middleware enabled
- [ ] Rate limiting middleware configured
- [ ] Authentication middleware enabled
- [ ] Request size limits configured
- [ ] Request logging enabled

#### Input Validation
- [ ] All API endpoints use Pydantic validation
- [ ] UUID validation for ID parameters
- [ ] Range validation for pagination
- [ ] String length limits defined

### 6. Monitoring & Logging

#### Logging
- [ ] Centralized logging configured (ELK, Splunk, CloudWatch)
- [ ] Log retention policy defined (90+ days recommended)
- [ ] Sensitive data sanitization verified
- [ ] Log rotation configured

#### Monitoring
- [ ] Application performance monitoring (APM)
- [ ] Error tracking configured (Sentry, Rollbar)
- [ ] Security event monitoring enabled
- [ ] Uptime monitoring configured

#### Alerting
- [ ] Authentication failure alerts
- [ ] Rate limit violation alerts
- [ ] Error rate threshold alerts
- [ ] Downtime alerts

### 7. Access Control

#### Authentication
- [ ] Dashboard password is strong and unique
- [ ] Password rotation schedule defined
- [ ] No default credentials in use
- [ ] Authentication logs monitored

#### Authorization
- [ ] All `/api/*` endpoints require authentication
- [ ] Public endpoints documented and minimal
- [ ] Least privilege access to all resources

#### Network Access
- [ ] VPC/private network for internal services
- [ ] Security groups configured
- [ ] Network ACLs in place
- [ ] VPN required for admin access (optional)

### 8. Data Protection

#### Encryption
- [ ] Database encryption at rest enabled
- [ ] Backups encrypted
- [ ] Secrets encrypted in secrets manager
- [ ] TLS for all data in transit

#### Data Retention
- [ ] Data retention policy defined
- [ ] Old data purge schedule configured
- [ ] Anonymization for historical data (optional)
- [ ] Compliance requirements met (GDPR, etc.)

### 9. Backup & Recovery

- [ ] Database backups automated
- [ ] Backup retention policy defined
- [ ] Backups stored in separate location
- [ ] Backup restoration tested
- [ ] Disaster recovery plan documented
- [ ] RTO/RPO defined

### 10. Compliance

#### Documentation
- [ ] Security documentation up to date (SECURITY.md)
- [ ] Incident response plan documented
- [ ] Data processing agreements in place
- [ ] Privacy policy updated

#### Audit
- [ ] Audit logging enabled
- [ ] Log integrity verified
- [ ] Access logs retained
- [ ] Compliance requirements identified

---

## Post-Deployment Verification

### 1. Security Headers Test

```bash
# Test security headers
curl -I https://api.example.com/health

# Should include:
# X-Content-Type-Options: nosniff
# X-Frame-Options: DENY
# Strict-Transport-Security: max-age=31536000
# Content-Security-Policy: ...
```

### 2. Authentication Test

```bash
# Test without password (should fail)
curl https://api.example.com/api/issues
# Expected: 401 Unauthorized

# Test with wrong password (should fail)
curl -H "X-Dashboard-Password: wrong" https://api.example.com/api/issues
# Expected: 403 Forbidden

# Test with correct password (should succeed)
curl -H "X-Dashboard-Password: correct_password" https://api.example.com/api/issues
# Expected: 200 OK
```

### 3. Rate Limiting Test

```bash
# Make 6 requests rapidly to auth endpoint
for i in {1..6}; do
  curl -H "X-Dashboard-Password: wrong" https://api.example.com/api/issues
done
# 6th request should return: 429 Too Many Requests
```

### 4. CORS Test

```bash
# Test CORS preflight
curl -X OPTIONS https://api.example.com/api/issues \
  -H "Origin: https://dashboard.example.com" \
  -H "Access-Control-Request-Method: GET" \
  -v

# Should include:
# Access-Control-Allow-Origin: https://dashboard.example.com
# Access-Control-Allow-Methods: GET, POST, PUT, PATCH, DELETE, OPTIONS
```

### 5. HTTPS Test

```bash
# Verify HTTPS is working
curl -I https://api.example.com/health
# Should return 200 OK

# Verify HTTP redirects to HTTPS (if configured)
curl -I http://api.example.com/health
# Should return 301/302 redirect to HTTPS
```

### 6. Database Connection Test

```bash
# From application server
psql "postgresql://user:pass@db.example.com:5432/prod_db?sslmode=require"

# Should connect with SSL
# Verify: \conninfo
# Should show SSL connection
```

### 7. Logging Test

```bash
# Trigger various events and verify logs
# 1. Successful request
curl -H "X-Dashboard-Password: correct" https://api.example.com/api/issues

# 2. Failed authentication
curl -H "X-Dashboard-Password: wrong" https://api.example.com/api/issues

# 3. Rate limit violation
for i in {1..6}; do curl -H "X-Dashboard-Password: wrong" https://api.example.com/api/issues; done

# Verify logs contain:
# - Request method, path, client IP
# - Response status, duration
# - Authentication failures
# - Rate limit violations
# - NO sensitive data (passwords, tokens)
```

---

## Security Monitoring - First 24 Hours

### What to Monitor

#### Application Logs
- [ ] No unexpected errors
- [ ] No authentication failures (beyond expected)
- [ ] Request response times acceptable
- [ ] No rate limit violations (beyond testing)

#### Security Events
- [ ] No suspicious IP addresses
- [ ] No brute force attempts
- [ ] No unusual access patterns
- [ ] No unexpected API usage

#### Performance
- [ ] Response times < 500ms average
- [ ] Error rate < 1%
- [ ] Database connection pool healthy
- [ ] Memory/CPU usage normal

#### External Monitoring
- [ ] Uptime monitoring shows 100%
- [ ] SSL certificate valid
- [ ] DNS resolving correctly
- [ ] CDN/WAF functioning (if applicable)

---

## Regular Security Maintenance

### Daily
- [ ] Review error logs
- [ ] Check authentication failures
- [ ] Monitor rate limit violations
- [ ] Verify backups completed

### Weekly
- [ ] Review access logs for anomalies
- [ ] Check for dependency updates
- [ ] Verify monitoring alerts working
- [ ] Review security event logs

### Monthly
- [ ] Update dependencies
- [ ] Run security scans (bandit, safety)
- [ ] Review CORS configuration
- [ ] Test backup restoration
- [ ] Review rate limit settings

### Quarterly
- [ ] Rotate API keys and credentials
- [ ] Security code review
- [ ] Penetration testing (optional)
- [ ] Update security documentation
- [ ] Review and update incident response plan

### Annually
- [ ] Comprehensive security audit
- [ ] Disaster recovery drill
- [ ] Review compliance requirements
- [ ] Security awareness training
- [ ] Third-party security assessment

---

## Incident Response Quick Reference

### 1. Suspected Breach

**Immediate Actions**:
1. [ ] Isolate affected systems
2. [ ] Rotate all credentials immediately
3. [ ] Review access logs
4. [ ] Identify scope of breach
5. [ ] Notify security team

### 2. Authentication Failures Spike

**Actions**:
1. [ ] Identify source IPs
2. [ ] Block suspicious IPs at firewall
3. [ ] Verify rate limiting is working
4. [ ] Review authentication logs
5. [ ] Consider temporary password rotation

### 3. API Abuse Detected

**Actions**:
1. [ ] Identify abuse pattern
2. [ ] Increase rate limits temporarily
3. [ ] Block abusive IPs
4. [ ] Review API logs
5. [ ] Add additional rate limiting if needed

### 4. Dependency Vulnerability

**Actions**:
1. [ ] Assess severity (CVSS score)
2. [ ] Check if vulnerability is exploitable
3. [ ] Update dependency immediately if critical
4. [ ] Test application after update
5. [ ] Deploy fix
6. [ ] Review logs for exploitation attempts

---

## Security Contact Information

**Security Issues**: [security@example.com]
**On-Call Security**: [phone/pager]
**Incident Response Team**: [team contact]
**Security Documentation**: See SECURITY.md

---

## Tools & Resources

### Security Testing Tools
- **Bandit**: Python security linter
  ```bash
  pip install bandit
  bandit -r backend/app/
  ```

- **Safety**: Dependency vulnerability scanner
  ```bash
  pip install safety
  safety check --file requirements.txt
  ```

- **OWASP ZAP**: Web application scanner
  ```bash
  docker run -t owasp/zap2docker-stable zap-baseline.py -t https://api.example.com
  ```

### Security Headers Testing
- https://securityheaders.com/
- https://observatory.mozilla.org/

### SSL/TLS Testing
- https://www.ssllabs.com/ssltest/

---

**Last Updated**: 2024-12-06
**Version**: 1.0
**Next Review**: Monthly or after significant changes
