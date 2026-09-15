# EdgeLog Deployment Guide

This guide covers deploying EdgeLog to production.

## Production Architecture

```
Internet → Load Balancer → Web Servers (Frontend)
                        → API Servers (Backend)
                        → PostgreSQL Database
```

## Prerequisites

- Production server (Linux recommended)
- PostgreSQL 16+ database server
- Domain name with SSL certificate
- Node.js 18+ for building frontend
- Python 3.11+ for backend
- Process manager (systemd or supervisor)
- Reverse proxy (nginx recommended)

## Database Setup

### 1. Create Production Database

```bash
# On database server
sudo -u postgres psql

CREATE DATABASE edgelog_prod;
CREATE USER edgelog_prod WITH PASSWORD 'strong_random_password_here';
GRANT ALL PRIVILEGES ON DATABASE edgelog_prod TO edgelog_prod;
\c edgelog_prod
GRANT ALL ON SCHEMA public TO edgelog_prod;
GRANT CREATE ON SCHEMA public TO edgelog_prod;
\q
```

### 2. Configure PostgreSQL for Network Access

Edit `/etc/postgresql/16/main/postgresql.conf`:
```
listen_addresses = 'localhost'  # Or specific IP
max_connections = 100
```

Edit `/etc/postgresql/16/main/pg_hba.conf`:
```
# Allow edgelog_prod user to connect
host    edgelog_prod    edgelog_prod    127.0.0.1/32    scram-sha-256
```

Restart PostgreSQL:
```bash
sudo systemctl restart postgresql
```

## Backend Deployment

### 1. Set Up Application Directory

```bash
sudo mkdir -p /var/www/edgelog/backend
sudo chown your_user:your_user /var/www/edgelog/backend
cd /var/www/edgelog/backend
```

### 2. Clone and Install

```bash
# Clone repository (or rsync files)
git clone https://github.com/khammrich1/edgelog.git .
# OR
rsync -av --exclude='node_modules' --exclude='venv' local/backend/ /var/www/edgelog/backend/

# Set up Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Production Environment

Create `/var/www/edgelog/backend/.env`:
```bash
# Database
DATABASE_URL=postgresql+asyncpg://edgelog_prod:PASSWORD@localhost/edgelog_prod

# Security - Generate new secrets for production!
SECRET_KEY=generate_with_secrets_token_urlsafe_32
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS - Your production domain(s)
ALLOWED_ORIGINS=["https://edgelog.trade"]

# Cookies - IMPORTANT: Set these correctly for production
COOKIE_SECURE=true
COOKIE_SAMESITE=lax
COOKIE_DOMAIN=edgelog.trade

# Environment
ENVIRONMENT=production

# AI screenshot trade capture (optional) - enables the screenshot-upload
# dropzone on the trades form. Leave blank to disable it; the app falls
# back to manual entry with no other impact.
ANTHROPIC_API_KEY=
```

**Security Notes:**
- Generate new SECRET_KEY: `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`
- Set COOKIE_SECURE=true for HTTPS
- Use your actual production domain in COOKIE_DOMAIN and ALLOWED_ORIGINS
- Never commit .env file to version control
- ANTHROPIC_API_KEY is only needed if you want screenshot-based trade capture; get a key from the Anthropic Console

### 4. Run Migrations

```bash
source venv/bin/activate
alembic upgrade head
```

### 5. Create Systemd Service

Create `/etc/systemd/system/edgelog-backend.service`:
```ini
[Unit]
Description=EdgeLog Backend API
After=network.target postgresql.service

[Service]
Type=simple
User=your_user
WorkingDirectory=/var/www/edgelog/backend
Environment="PATH=/var/www/edgelog/backend/venv/bin"
Environment="PYTHONPATH=/var/www/edgelog/backend"
ExecStart=/var/www/edgelog/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4 --proxy-headers --forwarded-allow-ips=127.0.0.1
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable edgelog-backend
sudo systemctl start edgelog-backend
sudo systemctl status edgelog-backend
```

## Frontend Deployment

### 1. Build Frontend

```bash
cd frontend
npm install
npm run build
```

This creates an optimized production build in `frontend/dist/`.

**No `VITE_API_URL` or other API-host environment variable is needed.** The
frontend calls the API with relative paths (`/api/v1/...`), which the browser
resolves against whatever origin served the page. As long as Nginx serves the
frontend and proxies `/api/` from that same origin/domain (see below), this
"just works" over HTTPS with no build-time configuration. Hard-coding an
absolute API URL (especially with `http://` instead of `https://`) is exactly
what causes the frontend to issue a request to the wrong scheme, which the
browser then treats as cross-origin and blocks with a CORS error after the
inevitable redirect to HTTPS.

### 2. Deploy Static Files

```bash
# Copy build to web server directory
sudo mkdir -p /var/www/edgelog/frontend
sudo cp -r dist/* /var/www/edgelog/frontend/
sudo chown -R www-data:www-data /var/www/edgelog/frontend
```

## Nginx Configuration

### 1. Install Nginx

```bash
sudo apt update
sudo apt install nginx
```

### 2. Configure Site

Use the version-controlled config at [`deploy/nginx/edgelog.conf`](deploy/nginx/edgelog.conf) —
don't hand-type an Nginx config from scratch; copy this file so the deployed
config can never drift from what's reviewed and committed here:

```bash
sudo cp deploy/nginx/edgelog.conf /etc/nginx/sites-available/edgelog
```

It redirects all HTTP to HTTPS, serves the built frontend from `/`, and
proxies `/api/` to the backend on the same origin — which is what lets the
frontend use plain relative API paths instead of a hard-coded host.

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/edgelog /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## SSL Certificate (Let's Encrypt)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d edgelog.trade

# Auto-renewal is configured by default
# Test renewal:
sudo certbot renew --dry-run
```

## Database Backup Strategy

### 1. Automated Backups

Create `/usr/local/bin/backup-edgelog-db.sh`:
```bash
#!/bin/bash
BACKUP_DIR="/var/backups/edgelog"
DATE=$(date +%Y%m%d_%H%M%S)
FILENAME="edgelog_prod_${DATE}.sql.gz"

mkdir -p $BACKUP_DIR
pg_dump -U edgelog_prod edgelog_prod | gzip > $BACKUP_DIR/$FILENAME

# Keep only last 30 days
find $BACKUP_DIR -name "edgelog_prod_*.sql.gz" -mtime +30 -delete

# Optional: Upload to S3 or backup service
```

Make executable:
```bash
sudo chmod +x /usr/local/bin/backup-edgelog-db.sh
```

Add to crontab (daily at 2 AM):
```bash
0 2 * * * /usr/local/bin/backup-edgelog-db.sh
```

### 2. Restore from Backup

```bash
gunzip -c /var/backups/edgelog/edgelog_prod_TIMESTAMP.sql.gz | \
  psql -U edgelog_prod -d edgelog_prod
```

## Monitoring

### 1. Application Logs

```bash
# Backend logs
sudo journalctl -u edgelog-backend -f

# Nginx access logs
sudo tail -f /var/log/nginx/access.log

# Nginx error logs
sudo tail -f /var/log/nginx/error.log
```

### 2. Health Checks

Create a simple health check endpoint and monitor it:
```bash
# Check backend is responding
curl -f https://edgelog.trade/api/v1/auth/login || echo "Backend down!"
```

## Scaling Considerations

### Horizontal Scaling

1. **Load Balancer**: Use nginx or HAProxy to distribute traffic across multiple backend instances
2. **Database**: Consider read replicas for high-traffic scenarios
3. **Static Assets**: Use CDN (CloudFlare, CloudFront) for frontend assets

### Vertical Scaling

Adjust uvicorn workers based on CPU cores:
```bash
# In systemd service file
ExecStart=/var/www/edgelog/backend/venv/bin/uvicorn app.main:app \
  --host 127.0.0.1 \
  --port 8000 \
  --workers 4 \
  --proxy-headers \
  --forwarded-allow-ips=127.0.0.1
```

Rule of thumb: workers = (2 × CPU cores) + 1

## Security Checklist

- [ ] PostgreSQL password is strong and random
- [ ] SECRET_KEY is generated fresh for production
- [ ] COOKIE_SECURE=true for HTTPS
- [ ] ALLOWED_ORIGINS includes only your production domain
- [ ] SSL certificate is valid and auto-renewing
- [ ] Security headers are configured in nginx
- [ ] Database backups are automated
- [ ] Application logs are monitored
- [ ] Firewall is configured (ufw or iptables)
- [ ] SSH is key-based only, no password authentication
- [ ] fail2ban is installed and configured

## Updating the Application

### Backend Updates

```bash
cd /var/www/edgelog/backend
source venv/bin/activate

# Pull latest code
git pull origin main

# Update dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Restart service
sudo systemctl restart edgelog-backend
```

### Frontend Updates

```bash
cd /path/to/local/edgelog/frontend

# Pull latest code
git pull origin main

# Rebuild
npm install
npm run build

# Deploy
sudo rsync -av dist/ /var/www/edgelog/frontend/

# Clear nginx cache if needed
sudo systemctl reload nginx
```

## Rollback Procedure

### Backend Rollback

```bash
# Rollback migration
alembic downgrade -1

# Restart with previous code
git checkout <previous-commit>
sudo systemctl restart edgelog-backend
```

### Database Rollback

```bash
# Restore from backup
sudo -u postgres psql
DROP DATABASE edgelog_prod;
CREATE DATABASE edgelog_prod;
\q

gunzip -c /var/backups/edgelog/edgelog_prod_TIMESTAMP.sql.gz | \
  sudo -u postgres psql -d edgelog_prod
```

## Support

For deployment issues:
1. Check application logs: `sudo journalctl -u edgelog-backend -f`
2. Check nginx logs: `sudo tail -f /var/log/nginx/error.log`
3. Verify database connection: `psql -U edgelog_prod -d edgelog_prod`
4. Test backend directly: `curl http://127.0.0.1:8000/api/v1/auth/login`
