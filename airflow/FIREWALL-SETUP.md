# Firewall Configuration for Airflow

## ✅ Ports Opened

```bash
# Airflow Web UI
firewall-cmd --permanent --add-port=8888/tcp

# AI Assistant API
firewall-cmd --permanent --add-port=8080/tcp

# Apply changes
firewall-cmd --reload
```

## 📊 Current Configuration

```bash
$ firewall-cmd --list-ports
8080/tcp 8888/tcp  ✅
```

## 🔍 Verification

```bash
# Check firewall status
firewall-cmd --state
# Output: running

# List all open ports
firewall-cmd --list-ports
# Output: 8080/tcp 8888/tcp

# Test Airflow UI (from host)
curl http://localhost:8888/health
# Should return JSON with status

# Test from browser
http://localhost:8888
# or
http://<your-ip>:8888
```

## 🚀 Access URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| **Airflow UI** | http://localhost:8888 | admin / admin |
| **AI Assistant** | http://localhost:8080 | (no auth) |
| **Cockpit** | https://localhost:9090 | (system user) |

## 🔒 Security Notes

### Current Setup (Development)
```
✅ Port 8888 (Airflow) - Open
✅ Port 8080 (AI Assistant) - Open
✅ Port 22 (SSH) - Open
✅ Port 9090 (Cockpit) - Open
```

### Production Recommendations

1. **Use Reverse Proxy**
   ```bash
   # Instead of exposing 8888 directly, use nginx/haproxy
   firewall-cmd --permanent --remove-port=8888/tcp
   firewall-cmd --permanent --add-service=http
   firewall-cmd --permanent --add-service=https
   ```

2. **Enable SSL/TLS**
   ```bash
   # Get certificates (Let's Encrypt)
   # Configure in docker-compose or reverse proxy
   ```

3. **Add Authentication**
   ```yaml
   # docker-compose.yml
   AIRFLOW__API__AUTH_BACKENDS: 'airflow.api.auth.backend.basic_auth'
   ```

4. **Restrict Source IPs**
   ```bash
   # Only allow from specific networks
   firewall-cmd --permanent --add-rich-rule='
     rule family="ipv4"
     source address="10.0.0.0/8"
     port protocol="tcp" port="8888" accept'
   ```

## 🛠️ Useful Commands

### Check What's Using Ports

```bash
# Show what's listening on 8888
ss -tlnp | grep 8888
# or
lsof -i :8888

# Show all open ports
ss -tlnp
```

### Firewall Management

```bash
# Check status
firewall-cmd --state

# List all rules
firewall-cmd --list-all

# Add port temporarily (until reboot)
firewall-cmd --add-port=8888/tcp

# Add port permanently
firewall-cmd --permanent --add-port=8888/tcp
firewall-cmd --reload

# Remove port
firewall-cmd --permanent --remove-port=8888/tcp
firewall-cmd --reload

# Open service (predefined ports)
firewall-cmd --permanent --add-service=http
firewall-cmd --permanent --add-service=https
```

### Test Connectivity

```bash
# From localhost
curl http://localhost:8888

# From another machine (replace IP)
curl http://192.168.1.100:8888

# Test if port is reachable
nc -zv localhost 8888
# or
telnet localhost 8888
```

## 🔧 Troubleshooting

### Issue: Can't access UI from browser

**Check 1: Is service running?**
```bash
podman ps | grep airflow_airflow-webserver
# Should show: Up X minutes (healthy)
```

**Check 2: Is port open on firewall?**
```bash
firewall-cmd --list-ports | grep 8888
# Should show: 8888/tcp
```

**Check 3: Is it listening?**
```bash
ss -tlnp | grep 8888
# Should show: LISTEN ... 0.0.0.0:8888
```

**Check 4: Can localhost access it?**
```bash
curl http://localhost:8888
# Should return HTML or JSON
```

**Check 5: SELinux blocking?**
```bash
getenforce
# If "Enforcing", check:
ausearch -m avc -ts recent | grep 8888
```

### Issue: Port already in use

```bash
# Find what's using the port
lsof -i :8888

# Kill the process (if safe)
kill <PID>

# Or use different port in docker-compose.yml
ports:
  - "8889:8080"  # Changed from 8888
```

### Issue: Firewall changes not applying

```bash
# Reload firewall
firewall-cmd --reload

# If that doesn't work, restart service
systemctl restart firewalld

# Verify changes
firewall-cmd --list-ports
```

## 📋 Quick Setup Script

```bash
#!/bin/bash
# Setup firewall for Airflow and AI Assistant

echo "🔧 Opening ports for Airflow deployment..."

# Add ports
firewall-cmd --permanent --add-port=8888/tcp
firewall-cmd --permanent --add-port=8080/tcp

# Reload
firewall-cmd --reload

# Verify
echo ""
echo "✅ Firewall configuration:"
firewall-cmd --list-ports

echo ""
echo "🧪 Testing connectivity..."
curl -s http://localhost:8888/health > /dev/null && echo "✅ Airflow UI: http://localhost:8888" || echo "❌ Airflow UI not responding"
curl -s http://localhost:8080/health > /dev/null && echo "✅ AI Assistant: http://localhost:8080" || echo "⚠️  AI Assistant not responding"

echo ""
echo "🎉 Setup complete!"
echo "   Access Airflow at: http://localhost:8888"
echo "   Login: admin / admin"
```

Save as `/root/qubinode_navigator/airflow/setup-firewall.sh` and run:
```bash
chmod +x setup-firewall.sh
./setup-firewall.sh
```

## ✅ Current Status

```bash
$ firewall-cmd --list-ports
8080/tcp 8888/tcp

$ ss -tlnp | grep -E '8080|8888'
LISTEN  0.0.0.0:8080  (AI Assistant)
LISTEN  0.0.0.0:8888  (Airflow UI)

$ curl http://localhost:8888/health
{"metadatabase": {"status": "healthy"}, "scheduler": {"status": "healthy"}}
```

✅ **Firewall configured correctly!**  
✅ **Airflow UI accessible!**  
✅ **Ready to use!**

---

**Last Updated:** 2025-11-20 01:15 UTC  
**Ports Opened:** 8080/tcp, 8888/tcp
