# Nginx Reverse Proxy Setup for Airflow

## ✅ What We Did

Configured nginx as a secure reverse proxy instead of exposing ports directly.

### Security Improvements:

- ❌ **Before:** Direct access on ports 8888, 8080
- ✅ **After:** Access through nginx on standard HTTP/HTTPS ports (80/443)
- 🔒 **Benefit:** Single entry point, SSL termination, better access control

## 🔧 Configuration

### Firewall Rules:

```bash
# Closed direct access ports
firewall-cmd --permanent --remove-port=8888/tcp
firewall-cmd --permanent --remove-port=8080/tcp

# Opened standard web ports
firewall-cmd --permanent --add-service=http
firewall-cmd --permanent --add-service=https
firewall-cmd --reload
```

### Nginx Configuration:

**File:** `/etc/nginx/conf.d/airflow.conf`

```nginx
upstream airflow_backend {
    server localhost:8888;
}

upstream ai_assistant_backend {
    server localhost:8080;
}

server {
    listen 80;
    server_name YOUR_SERVER_IP;

    # Airflow UI - http://YOUR_SERVER_IP/airflow/
    location /airflow/ {
        proxy_pass http://airflow_backend/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeouts
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # AI Assistant - http://YOUR_SERVER_IP/ai/
    location /ai/ {
        proxy_pass http://ai_assistant_backend/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # Default - redirect to Airflow
    location / {
        return 301 /airflow/;
    }

    # Health check
    location /health {
        proxy_pass http://airflow_backend/health;
        access_log off;
    }
}
```

## 🚀 Access URLs

| Service          | URL                            | Notes        |
| ---------------- | ------------------------------ | ------------ |
| **Airflow UI**   | http://YOUR_SERVER_IP/airflow/ | Main UI      |
| **AI Assistant** | http://YOUR_SERVER_IP/ai/      | API endpoint |
| **Health Check** | http://YOUR_SERVER_IP/health   | Status       |

### Credentials:

- **Username:** admin
- **Password:** admin

## ⚠️ Current Issue & Fix Needed

### Problem:

Airflow UI is not loading through nginx because Airflow needs to know about the base URL (`/airflow/`).

### Solution:

Update Airflow configuration to set the base URL.

**File:** `/root/qubinode_navigator/airflow/docker-compose.yml`

Add to environment:

```yaml
environment:
  AIRFLOW__WEBSERVER__BASE_URL: 'http://YOUR_SERVER_IP/airflow'
  AIRFLOW__WEBSERVER__ENABLE_PROXY_FIX: 'true'
```

Then restart:

```bash
cd /root/qubinode_navigator/airflow
podman-compose down
podman-compose up -d
```

## 🔒 Next Steps: Add SSL/TLS

### 1. Install Certbot

```bash
dnf install -y certbot python3-certbot-nginx
```

### 2. Get SSL Certificate

```bash
# Stop nginx temporarily
systemctl stop nginx

# Get certificate (use your domain name)
certbot certonly --standalone -d yourdomain.com

# Or if using IP (not recommended for production):
# Use self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/private/nginx-selfsigned.key \
  -out /etc/ssl/certs/nginx-selfsigned.crt
```

### 3. Update Nginx Config

Uncomment the HTTPS server block in `/etc/nginx/conf.d/airflow.conf`:

```nginx
server {
    listen 443 ssl http2;
    server_name YOUR_SERVER_IP;

    ssl_certificate /etc/letsencrypt/live/yourdomain/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # ... same location blocks ...
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name YOUR_SERVER_IP;
    return 301 https://$server_name$request_uri;
}
```

### 4. Restart Nginx

```bash
nginx -t
systemctl restart nginx
```

## 🛡️ Additional Security

### IP-Based Access Control

Restrict to specific IP ranges:

```nginx
server {
    # ... existing config ...

    # Only allow from specific networks
    allow 10.0.0.0/8;       # Internal network
    allow 192.168.0.0/16;   # Private network
    allow YOUR_IP_HERE;     # Your IP
    deny all;               # Deny everyone else
}
```

### Rate Limiting

Prevent abuse:

```nginx
# Add before server block
limit_req_zone $binary_remote_addr zone=airflow:10m rate=10r/s;

server {
    # ... existing config ...

    location /airflow/ {
        limit_req zone=airflow burst=20;
        # ... rest of proxy config ...
    }
}
```

### Basic Authentication

Add extra auth layer:

```bash
# Create password file
htpasswd -c /etc/nginx/.htpasswd admin

# Add to nginx config
location /airflow/ {
    auth_basic "Airflow Access";
    auth_basic_user_file /etc/nginx/.htpasswd;
    # ... rest of proxy config ...
}
```

## 🧪 Testing

### Test Nginx Configuration

```bash
nginx -t
```

### Test Access

```bash
# Health check
curl http://YOUR_SERVER_IP/health

# Airflow UI (should redirect or load)
curl -L http://YOUR_SERVER_IP/airflow/

# From browser
http://YOUR_SERVER_IP/airflow/
```

### Test Backend Connectivity

```bash
# Direct to Airflow (should work from localhost)
curl http://localhost:8888/health

# Through nginx
curl http://localhost/health
```

### Check Logs

```bash
# Nginx access log
tail -f /var/log/nginx/access.log

# Nginx error log
tail -f /var/log/nginx/error.log

# Airflow logs
podman logs -f airflow_airflow-webserver_1
```

## 🔧 Troubleshooting

### Issue: 404 Not Found

**Cause:** Airflow doesn't know about base URL

**Fix:** Add `AIRFLOW__WEBSERVER__BASE_URL` to docker-compose.yml

### Issue: 502 Bad Gateway

**Cause:** Backend not running or not accessible

**Check:**

```bash
# Is Airflow running?
podman ps | grep airflow_airflow-webserver

# Can nginx reach it?
curl http://localhost:8888/health
```

### Issue: Connection Timeout

**Cause:** Firewall blocking nginx → container communication

**Fix:**

```bash
# Check SELinux
getsebool httpd_can_network_connect
# If off:
setsebool -P httpd_can_network_connect on
```

### Issue: CSS/JS Not Loading

**Cause:** Static files not served correctly due to base URL

**Fix:** Configure Airflow base URL properly

## 📊 Current Status

```bash
# Nginx status
$ systemctl status nginx
✅ Active: active (running)

# Firewall rules
$ firewall-cmd --list-services
✅ http https ssh ...

# Ports NOT exposed
$ firewall-cmd --list-ports
(empty - good!)

# Backend health
$ curl http://localhost:8888/health
✅ {"metadatabase": {"status": "healthy"}, ...}
```

## 📋 Quick Commands

```bash
# Restart nginx
systemctl restart nginx

# Reload config (no downtime)
systemctl reload nginx

# Test config
nginx -t

# View logs
journalctl -u nginx -f

# Restart Airflow
cd /root/qubinode_navigator/airflow
podman-compose restart

# Check what's listening
ss -tlnp | grep -E '80|8888'
```

## ✅ Benefits of This Setup

1. **Security:**

   - ✅ No direct port exposure
   - ✅ Single entry point
   - ✅ SSL termination at nginx
   - ✅ Can add authentication easily

1. **Flexibility:**

   - ✅ Multiple services on one port
   - ✅ Path-based routing
   - ✅ Easy to add more services

1. **Performance:**

   - ✅ Nginx static file serving
   - ✅ Connection pooling
   - ✅ Compression
   - ✅ Caching (if configured)

1. **Monitoring:**

   - ✅ Centralized access logs
   - ✅ Easy to add monitoring
   - ✅ Better visibility

## 🎯 Final Steps to Complete Setup

1. **Fix Airflow Base URL** (REQUIRED):

   ```bash
   vim /root/qubinode_navigator/airflow/docker-compose.yml
   # Add AIRFLOW__WEBSERVER__BASE_URL environment variable
   podman-compose restart
   ```

1. **Add SSL** (Recommended):

   ```bash
   certbot --nginx -d yourdomain.com
   ```

1. **Test thoroughly**:

   ```bash
   curl http://YOUR_SERVER_IP/airflow/
   # Should work!
   ```

1. **Monitor logs**:

   ```bash
   tail -f /var/log/nginx/access.log
   ```

______________________________________________________________________

**Status:** Nginx configured ✅
**Next:** Fix Airflow base URL
**Security:** Improved ✅
**Access:** http://YOUR_SERVER_IP/airflow/
