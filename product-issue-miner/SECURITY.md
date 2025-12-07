# Security Documentation

## Table of Contents

1. [Overview](#overview)
2. [Authentication & Authorization](#authentication--authorization)
3. [Security Headers](#security-headers)
4. [Rate Limiting](#rate-limiting)
5. [Input Validation](#input-validation)
6. [Credential Management](#credential-management)
7. [CORS Configuration](#cors-configuration)
8. [Data Sanitization](#data-sanitization)
9. [Monitoring & Logging](#monitoring--logging)
10. [Security Best Practices](#security-best-practices)
11. [Incident Response](#incident-response)
12. [Security Checklist](#security-checklist)

---

## Overview

The Product Issue Miner application implements multiple layers of security controls appropriate for an internal tool handling sensitive Zendesk and customer data. This document outlines the security architecture, configuration guidelines, and best practices.

### Security Principles

- **Defense in Depth**: Multiple security layers protect against various attack vectors
- **Least Privilege**: Minimal permissions for all components and users
- **Secure by Default**: Security controls are enabled by default
- **Fail Securely**: Errors do not expose sensitive information
- **Input Validation**: All user input is validated and sanitized
- **Logging & Monitoring**: Security events are logged for audit and investigation

---

## Authentication & Authorization

### Current Implementation

The application uses **simple password-based authentication** via the `X-Dashboard-Password` HTTP header. This is suitable for internal tools with controlled access.

**Authentication Flow:**
```
Client Request → AuthenticationMiddleware → Verify Password → Allow/Deny
```

**Protected Endpoints:**
- All `/api/*` endpoints require authentication
- Public endpoints: `/`, `/health`, `/docs`, `/openapi.json`, `/redoc`

### Security Features

1. **Constant-Time Comparison**: Password verification uses constant-time comparison to prevent timing attacks
2. **Rate Limiting**: Authentication endpoints have strict rate limits (5 requests/minute by default)
3. **No Information Leakage**: Failed auth returns generic error messages
4. **Secure Headers**: Password transmitted via custom header (not query params or body)

### Password Requirements

**Minimum Security Standards:**
- Minimum length: 16 characters
- Use randomly generated passwords
- Avoid dictionary words and common patterns
- Rotate regularly (recommended: every 90 days)

**Generate Strong Password:**
```bash
# Generate a random 32-character password
openssl rand -base64 32

# Or use Python
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Future Enhancements

For production deployments with broader access, consider:

- **OAuth 2.0 / OpenID Connect**: Industry-standard authentication
- **JSON Web Tokens (JWT)**: Stateless token-based authentication
- **Multi-Factor Authentication (MFA)**: Additional security layer
- **API Key Management**: Per-user or per-service API keys
- **Session Management**: Time-limited sessions with refresh tokens
- **Role-Based Access Control (RBAC)**: Granular permissions

---

## Security Headers

The application implements OWASP-recommended security headers via `SecurityHeadersMiddleware`.

### Implemented Headers

#### 1. X-Content-Type-Options: nosniff
**Purpose**: Prevents MIME type sniffing attacks
**Protection**: Browsers will not interpret files as a different MIME type

#### 2. X-Frame-Options: DENY
**Purpose**: Prevents clickjacking attacks
**Protection**: Page cannot be embedded in frames/iframes

#### 3. X-XSS-Protection: 1; mode=block
**Purpose**: Enables browser XSS filter (legacy support)
**Protection**: Browser blocks detected XSS attempts

#### 4. Strict-Transport-Security (Production Only)
**Value**: `max-age=31536000; includeSubDomains; preload`
**Purpose**: Forces HTTPS connections
**Protection**: Prevents downgrade attacks and cookie hijacking
**Note**: Only enabled when `ENVIRONMENT=production`

#### 5. Content-Security-Policy (CSP)
**Directives**:
```
default-src 'self'
script-src 'self'
style-src 'self' 'unsafe-inline'
img-src 'self' data: https:
font-src 'self' data:
connect-src 'self'
frame-ancestors 'none'
base-uri 'self'
form-action 'self'
```

**Purpose**: Controls resource loading and prevents XSS
**Protection**: Restricts where resources can be loaded from

**Customization**: Adjust CSP directives in `backend/app/middleware/security.py` based on your frontend framework requirements.

#### 6. Referrer-Policy: strict-origin-when-cross-origin
**Purpose**: Controls referrer information sent with requests
**Protection**: Prevents leaking sensitive URLs to third parties

#### 7. Permissions-Policy
**Disabled Features**: geolocation, microphone, camera, payment, usb, magnetometer
**Purpose**: Restricts browser feature access
**Protection**: Reduces attack surface and privacy risks

### Testing Security Headers

```bash
# Test headers with curl
curl -I http://localhost:8000/health

# Test with online tools
# - https://securityheaders.com/
# - https://observatory.mozilla.org/
```

---

## Rate Limiting

Rate limiting protects against brute force attacks, DoS attempts, and API abuse.

### Configuration

**Environment Variables:**
```bash
# Authentication endpoints (stricter limits)
AUTH_RATE_LIMIT=5  # requests per minute per IP

# General API endpoints
GENERAL_RATE_LIMIT=100  # requests per minute per IP
```

### Implementation Details

- **Granularity**: Per IP address
- **Window**: Sliding 60-second window
- **Storage**: In-memory (default) or Redis (recommended for production)
- **Response**: HTTP 429 with `Retry-After` header

### Rate Limit Headers

All responses include rate limit information:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
```

When rate limited:
```
HTTP/1.1 429 Too Many Requests
Retry-After: 60
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
```

### Protected Endpoints

**Strict Limits** (5 req/min):
- `/api/auth`
- `/api/login`
- `/api/dashboard`

**General Limits** (100 req/min):
- All other `/api/*` endpoints

**Exempt**:
- `/health`
- `/`
- `/docs`
- `/openapi.json`

### Production Recommendations

For production deployments:

1. **Use Redis for Distributed Rate Limiting**:
   ```python
   # Install: pip install redis
   # Configure in middleware to use Redis backend
   ```

2. **Tune Limits Based on Usage**:
   - Monitor legitimate usage patterns
   - Set limits slightly above normal usage
   - Consider different limits for different endpoints

3. **Implement IP Whitelisting**:
   - Allow higher limits for trusted IPs
   - Bypass rate limiting for internal services

4. **Consider User-Based Rate Limiting**:
   - Rate limit per authenticated user instead of per IP
   - Prevents shared IP issues (NAT, proxies)

---

## Input Validation

All API inputs are validated using **Pydantic models** with strict type checking and validation rules.

### Validation Strategy

1. **Type Validation**: Pydantic enforces correct data types
2. **Range Validation**: Min/max values for numeric fields
3. **Pattern Validation**: Regex patterns for strings
4. **Enum Validation**: Restricted values for categorical fields
5. **Required Fields**: Explicit required/optional field definitions

### Example: Validated Schemas

```python
# backend/app/schemas/ticket.py
class TicketBase(BaseModel):
    zendesk_ticket_id: int  # Must be integer
    subject: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    ticket_created_at: datetime  # Must be valid datetime
```

### SQL Injection Prevention

**Protection Mechanisms:**

1. **SQLAlchemy ORM**: All database queries use ORM (not raw SQL)
2. **Parameterized Queries**: When raw SQL is needed, always use parameters
3. **Type Validation**: Pydantic validates input types before queries

**Safe Pattern:**
```python
# Using ORM (safe)
tickets = await session.execute(
    select(Ticket).where(Ticket.id == ticket_id)
)

# Parameterized query (safe)
result = await session.execute(
    text("SELECT * FROM tickets WHERE id = :id"),
    {"id": ticket_id}
)

# NEVER do this (vulnerable to SQL injection)
# result = await session.execute(f"SELECT * FROM tickets WHERE id = {ticket_id}")
```

### XSS Prevention

**Protection Mechanisms:**

1. **No Raw HTML Rendering**: API returns JSON, not HTML
2. **Frontend Sanitization**: Frontend responsible for sanitizing before rendering
3. **Content-Type Headers**: All responses are `application/json`
4. **CSP Headers**: Content-Security-Policy prevents inline script execution

**Frontend Responsibilities:**
- Sanitize user-generated content before rendering
- Use framework-provided escaping (React automatically escapes)
- Avoid `dangerouslySetInnerHTML` or sanitize with DOMPurify
- Validate data from API before rendering

---

## Credential Management

### Secure Storage

**✅ DO:**
- Store credentials in environment variables
- Use `.env` file for local development (add to `.gitignore`)
- Use secrets management systems in production (AWS Secrets Manager, HashiCorp Vault)
- Encrypt database credentials at rest
- Use separate credentials for each environment

**❌ DON'T:**
- Hard-code credentials in source code
- Commit `.env` files to version control
- Share credentials via email or chat
- Use the same credentials across environments
- Log credentials in application logs

### Environment Variables

**Required Credentials:**
```bash
ZENDESK_API_TOKEN=xxx          # Zendesk API authentication
ANTHROPIC_API_KEY=sk-ant-xxx   # Claude AI API key
DASHBOARD_PASSWORD=xxx         # Application authentication
DATABASE_URL=postgresql://xxx  # Database connection
```

**Masking in Logs:**

The application automatically masks sensitive values in logs:

```python
# backend/app/config.py
def __repr__(self) -> str:
    """Custom repr that masks sensitive values."""
    sensitive_fields = {
        "ZENDESK_API_TOKEN",
        "ANTHROPIC_API_KEY",
        "DASHBOARD_PASSWORD",
        "DATABASE_URL",
    }
    # Masks values as: abc123***xyz789
```

### API Key Rotation

**Rotation Schedule:**
- Development: As needed
- Production: Every 90 days
- After suspected compromise: Immediately

**Rotation Procedure:**

1. **Generate New Key**:
   - Zendesk: Settings → API → Add API Token
   - Anthropic: Console → API Keys → Create Key
   - Dashboard: `openssl rand -base64 32`

2. **Update Environment Variables**:
   - Update `.env` file (development)
   - Update secrets manager (production)
   - Restart application to load new values

3. **Verify New Key**:
   - Test API connectivity
   - Monitor logs for authentication errors

4. **Revoke Old Key**:
   - Wait 24-48 hours for propagation
   - Disable/delete old key in service console

### Secrets Management (Production)

**Recommended Solutions:**

1. **AWS Secrets Manager** (AWS deployments)
   ```python
   import boto3
   client = boto3.client('secretsmanager')
   secret = client.get_secret_value(SecretId='prod/app/keys')
   ```

2. **HashiCorp Vault** (Multi-cloud)
   ```python
   import hvac
   client = hvac.Client(url='https://vault.example.com')
   secret = client.secrets.kv.v2.read_secret_version(path='app/keys')
   ```

3. **Azure Key Vault** (Azure deployments)
   ```python
   from azure.keyvault.secrets import SecretClient
   client = SecretClient(vault_url="https://vault.azure.net", credential=credential)
   secret = client.get_secret("api-key")
   ```

4. **Kubernetes Secrets** (K8s deployments)
   ```yaml
   apiVersion: v1
   kind: Secret
   metadata:
     name: app-secrets
   type: Opaque
   data:
     zendesk-token: <base64-encoded>
     anthropic-key: <base64-encoded>
   ```

---

## CORS Configuration

Cross-Origin Resource Sharing (CORS) controls which domains can access the API.

### Configuration

**Environment Variable:**
```bash
# Development (multiple allowed origins)
CORS_ORIGINS=http://localhost:3000,http://localhost:3001

# Production (specific domains only)
CORS_ORIGINS=https://dashboard.example.com,https://app.example.com

# NEVER use in production
CORS_ORIGINS=*
```

### Security Considerations

**⚠️ WARNING**: Using `CORS_ORIGINS=*` in production is a critical security risk:
- Allows any website to access your API
- Exposes API to CSRF attacks
- Credentials can be stolen by malicious sites

The application will log a warning if wildcard CORS is detected in production:
```
WARNING: CORS is set to allow all origins (*) in production.
This is a security risk. Set CORS_ORIGINS to specific origins.
```

### Development vs Production

**Development:**
```bash
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
ENVIRONMENT=development
```

**Production:**
```bash
CORS_ORIGINS=https://app.production.com
ENVIRONMENT=production
```

### CORS Headers

**Allowed Methods:**
```
GET, POST, PUT, PATCH, DELETE, OPTIONS
```

**Allowed Headers:**
```
Content-Type, X-Dashboard-Password, Authorization
```

**Credentials:**
```
allow_credentials=True
```

**Preflight Cache:**
```
max_age=600  # Cache preflight for 10 minutes
```

### Testing CORS

```bash
# Test CORS preflight
curl -X OPTIONS http://localhost:8000/api/issues \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: GET" \
  -v

# Should return:
# Access-Control-Allow-Origin: http://localhost:3000
# Access-Control-Allow-Methods: GET, POST, PUT, PATCH, DELETE, OPTIONS
# Access-Control-Allow-Headers: Content-Type, X-Dashboard-Password, Authorization
```

---

## Data Sanitization

### Zendesk Data Handling

All data received from Zendesk is untrusted and must be sanitized before:
- Storing in database
- Sending to Claude AI
- Displaying in frontend

**Sanitization Steps:**

1. **Input Validation**: Validate data structure and types
2. **HTML Stripping**: Remove HTML from ticket descriptions
3. **Size Limits**: Truncate excessively long fields
4. **Character Filtering**: Remove control characters
5. **Encoding**: Ensure proper UTF-8 encoding

**Example: Zendesk Client**
```python
# backend/app/services/zendesk.py
def format_comments(self, comments: List[Dict[str, Any]]) -> str:
    """Format comments with sanitization."""
    body = (
        comment.get("plain_body") or  # Prefer plain text
        comment.get("body") or
        "(empty comment)"
    )
    # Additional sanitization can be added here
```

### Claude AI Input Sanitization

Before sending ticket data to Claude:

1. **Remove PII**: Strip email addresses, phone numbers (if required)
2. **Limit Size**: Truncate to prevent excessive token usage
3. **Format Validation**: Ensure proper structure for prompts
4. **Content Filtering**: Remove offensive or inappropriate content (optional)

### Database Storage

**Protection Mechanisms:**

1. **Type Validation**: Pydantic models enforce correct types
2. **Length Limits**: VARCHAR columns have max lengths
3. **Encoding**: UTF-8 encoding for all text fields
4. **Prepared Statements**: SQLAlchemy uses parameterized queries

---

## Monitoring & Logging

### Logging Strategy

**What is Logged:**
- Request method, path, client IP
- Response status code and duration
- Authentication failures
- Rate limit violations
- Application errors and exceptions

**What is NOT Logged:**
- Passwords or API keys
- Full request bodies (may contain sensitive data)
- Authorization headers
- Database connection strings

### Log Levels

**Configuration:**
```bash
LOG_LEVEL=INFO  # Development
LOG_LEVEL=WARNING  # Production
```

**Levels:**
- `DEBUG`: Detailed information for troubleshooting
- `INFO`: General informational messages
- `WARNING`: Warning messages (rate limits, security events)
- `ERROR`: Error messages (failures, exceptions)
- `CRITICAL`: Critical errors requiring immediate attention

### Sensitive Data Sanitization

**Automatic Sanitization:**
```python
# backend/app/middleware/security.py
SENSITIVE_HEADERS = {
    "authorization",
    "x-dashboard-password",
    "x-api-key",
    "cookie",
}

def _sanitize_headers(self, headers: Headers) -> Dict[str, str]:
    """Sanitize sensitive headers for logging."""
    for key, value in headers.items():
        if key.lower() in self.SENSITIVE_HEADERS:
            sanitized[key] = "***REDACTED***"
```

### Log Format

**Standard Format:**
```
2024-12-06 10:30:45 - app.main - INFO - Request: GET /api/issues from 192.168.1.100
2024-12-06 10:30:45 - app.main - INFO - Response: GET /api/issues -> 200 (45.23ms)
```

**Security Event:**
```
2024-12-06 10:31:15 - app.middleware.security - WARNING - Invalid authentication from 192.168.1.105
2024-12-06 10:31:20 - app.middleware.security - WARNING - Rate limit exceeded for 192.168.1.105
```

### Monitoring Recommendations

**Production Monitoring:**

1. **Centralized Logging**: Aggregate logs from all instances
   - ELK Stack (Elasticsearch, Logstash, Kibana)
   - Splunk
   - Datadog
   - CloudWatch Logs (AWS)

2. **Security Monitoring**:
   - Monitor authentication failures
   - Track rate limit violations
   - Alert on suspicious IP addresses
   - Monitor API key usage

3. **Performance Monitoring**:
   - Track response times
   - Monitor error rates
   - Alert on high latency

4. **Audit Trail**:
   - Log all data modifications
   - Track user actions
   - Retain logs for compliance (90+ days)

---

## Security Best Practices

### Application Security

#### 1. Keep Dependencies Updated
```bash
# Check for security vulnerabilities
pip install safety
safety check

# Update dependencies
pip list --outdated
pip install --upgrade <package>
```

#### 2. Use Security Scanners
```bash
# Static analysis
bandit -r backend/app/

# Dependency vulnerabilities
pip-audit

# SAST scanning
semgrep --config=auto backend/
```

#### 3. Secure Database Connections
```bash
# Use SSL/TLS for database connections
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db?ssl=require

# Use connection pooling with limits
# max_connections: 20
# min_connections: 5
```

#### 4. Environment Isolation
- Use separate environments (dev, staging, prod)
- Different credentials for each environment
- Network isolation between environments
- Separate databases for each environment

### Network Security

#### 1. Use HTTPS
- **Production**: Always use HTTPS (TLS 1.2+)
- **Certificate**: Use valid SSL/TLS certificates
- **Redirect**: Redirect HTTP to HTTPS
- **HSTS**: Enable Strict-Transport-Security header

#### 2. Firewall Rules
- Restrict database access to application servers only
- Allow API access only from frontend domains
- Block suspicious IP addresses
- Use VPC/private networks for internal services

#### 3. Reverse Proxy
Use Nginx or similar as reverse proxy:
```nginx
# Example Nginx config
location /api/ {
    proxy_pass http://localhost:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # Security headers
    add_header X-Frame-Options "DENY";
    add_header X-Content-Type-Options "nosniff";
}
```

### Data Security

#### 1. Encryption at Rest
- Encrypt database storage
- Encrypt backup files
- Encrypt log files containing sensitive data
- Use encrypted filesystems (e.g., LUKS, BitLocker)

#### 2. Encryption in Transit
- Use HTTPS for all API communication
- Use TLS for database connections
- Use secure protocols for Redis (TLS)

#### 3. Data Retention
- Define data retention policies
- Automatically purge old data
- Anonymize historical data
- Secure deletion of sensitive data

### Access Control

#### 1. Principle of Least Privilege
- Grant minimum necessary permissions
- Use separate accounts for different purposes
- Regularly audit access permissions

#### 2. Network Segmentation
- Isolate database in private network
- Use security groups/firewalls
- Implement network ACLs

---

## Incident Response

### Detection

**Indicators of Compromise:**
- Unusual authentication failures
- Spike in rate limit violations
- Unexpected API usage patterns
- Database access from unknown IPs
- Unusual error rates

**Monitoring Tools:**
- Application logs
- Security event logs
- Database audit logs
- Network traffic analysis

### Response Procedures

#### 1. Identify and Contain
```bash
# Review logs for suspicious activity
grep "Invalid authentication" /var/log/app/*.log

# Identify compromised credentials
# Immediately rotate affected API keys

# Block suspicious IPs (if needed)
# Add to firewall rules or WAF
```

#### 2. Investigate
- Determine scope of breach
- Identify compromised data
- Review access logs
- Preserve evidence for forensics

#### 3. Remediate
- Rotate all potentially compromised credentials
- Patch vulnerabilities
- Update security controls
- Deploy fixes

#### 4. Recover
- Restore from clean backups if needed
- Verify system integrity
- Monitor for continued suspicious activity

#### 5. Post-Incident Review
- Document incident timeline
- Identify root cause
- Update security procedures
- Implement preventive measures

### Breach Notification

**Legal Requirements:**
- GDPR: Notify within 72 hours of discovery
- HIPAA: Notify within 60 days
- State laws: Vary by jurisdiction

**Notification Process:**
1. Assess legal requirements
2. Notify affected users
3. Notify regulatory authorities (if required)
4. Document notification process

---

## Security Checklist

### Pre-Deployment Security Review

#### Environment Configuration
- [ ] Strong `DASHBOARD_PASSWORD` set (min 16 chars, random)
- [ ] `ENVIRONMENT` set to appropriate value
- [ ] `CORS_ORIGINS` restricted to specific domains (no `*`)
- [ ] `LOG_LEVEL` set appropriately (INFO or WARNING for prod)
- [ ] All API keys are production keys (not test keys)

#### Secrets Management
- [ ] `.env` file is in `.gitignore`
- [ ] No credentials hard-coded in source code
- [ ] Secrets stored in secure secrets manager (production)
- [ ] Secrets encrypted at rest
- [ ] API key rotation schedule established

#### Network Security
- [ ] Application runs behind HTTPS (production)
- [ ] Valid SSL/TLS certificate configured
- [ ] Database uses SSL/TLS connections
- [ ] Database accessible only from application servers
- [ ] Redis uses password authentication

#### Application Security
- [ ] All dependencies are up to date
- [ ] No critical security vulnerabilities (`safety check`)
- [ ] Security headers enabled
- [ ] Rate limiting configured and tested
- [ ] Input validation on all endpoints
- [ ] Request size limits configured

#### Monitoring & Logging
- [ ] Centralized logging configured
- [ ] Security event monitoring enabled
- [ ] Log retention policy defined
- [ ] Alerting configured for security events
- [ ] Logs do not contain sensitive data

#### Access Control
- [ ] Authentication enabled on all protected endpoints
- [ ] Least privilege access to database
- [ ] Separate credentials for each environment
- [ ] Network segmentation implemented

#### Backup & Recovery
- [ ] Database backups configured
- [ ] Backup retention policy defined
- [ ] Backup restoration tested
- [ ] Disaster recovery plan documented
- [ ] Secrets backup procedure established

#### Compliance
- [ ] Data retention policy compliant with regulations
- [ ] Privacy policy updated
- [ ] Data processing agreements in place
- [ ] Audit logging enabled
- [ ] Incident response plan documented

### Regular Security Audits

#### Monthly
- [ ] Review authentication logs for suspicious activity
- [ ] Check for security vulnerabilities in dependencies
- [ ] Review rate limit violations
- [ ] Verify backup integrity

#### Quarterly
- [ ] Rotate API keys and credentials
- [ ] Security code review
- [ ] Penetration testing (if applicable)
- [ ] Review and update security documentation

#### Annually
- [ ] Comprehensive security audit
- [ ] Disaster recovery drill
- [ ] Update incident response procedures
- [ ] Security awareness training

---

## Additional Resources

### OWASP Resources
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/)

### Security Testing Tools
- [Bandit](https://bandit.readthedocs.io/) - Python security linter
- [Safety](https://pyup.io/safety/) - Python dependency vulnerability scanner
- [OWASP ZAP](https://www.zaproxy.org/) - Web application security scanner
- [Semgrep](https://semgrep.dev/) - Static analysis tool

### Best Practices
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [CIS Controls](https://www.cisecurity.org/controls)
- [SANS Security Principles](https://www.sans.org/security-resources/)

---

## Contact

For security issues or questions:
- **Security Issues**: Report via [security contact/process]
- **General Questions**: [team contact]

**Last Updated**: 2024-12-06
**Version**: 1.0
