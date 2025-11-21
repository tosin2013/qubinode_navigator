#!/bin/bash
# =============================================================================
# Qubinode Navigator + Airflow Unified Deployment
# Deploys complete stack: AI Assistant + Airflow on shared network
# =============================================================================

set -euo pipefail

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
SERVER_IP="$(hostname -I | awk '{print $1}')"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${CYAN}"
cat << 'EOF'
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║     Qubinode Navigator + Airflow Unified Deployment           ║
║                                                                ║
║     • AI Assistant                                             ║
║     • Apache Airflow with kcli + virsh                         ║
║     • Nginx Reverse Proxy (Production-Ready)                   ║
║     • Shared Podman network                                    ║
║     • Integrated chat in Airflow UI                            ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Step 1: Deploy base infrastructure
echo -e "${BLUE}[1/4] Deploying base infrastructure...${NC}"
if [[ -f "$SCRIPT_DIR/deploy-qubinode.sh" ]]; then
    # Run the base deployment (handles hypervisor, AI Assistant, etc.)
    "$SCRIPT_DIR/deploy-qubinode.sh" || {
        echo -e "${RED}Base deployment failed${NC}"
        exit 1
    }
else
    echo -e "${BLUE}Skipping base deployment (not found)${NC}"
fi

# Step 2: Deploy Airflow
echo -e "${BLUE}[2/4] Deploying Airflow workflow orchestration...${NC}"
if [[ -f "$SCRIPT_DIR/airflow/deploy-airflow.sh" ]]; then
    "$SCRIPT_DIR/airflow/deploy-airflow.sh" deploy || {
        echo -e "${RED}Airflow deployment failed${NC}"
        exit 1
    }
else
    echo -e "${RED}Error: airflow/deploy-airflow.sh not found${NC}"
    exit 1
fi

# Step 3: Deploy Nginx Reverse Proxy
echo -e "${BLUE}[3/4] Setting up Nginx reverse proxy for secure access...${NC}"

# Install nginx if not present
if ! command -v nginx &> /dev/null; then
    echo -e "${CYAN}  Installing nginx...${NC}"
    dnf install -y nginx || {
        echo -e "${RED}Failed to install nginx${NC}"
        exit 1
    }
fi

# Create nginx configuration
echo -e "${CYAN}  Creating nginx configuration...${NC}"
cat > /etc/nginx/conf.d/airflow.conf << 'NGINX_EOF'
# Airflow and AI Assistant Reverse Proxy Configuration

# Upstream definitions
upstream airflow_backend {
    server localhost:8888;
}

upstream ai_assistant_backend {
    server localhost:8080;
}

# HTTP server
server {
    listen 80;
    server_name _;

    # Airflow UI at root
    location / {
        proxy_pass http://airflow_backend/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support for live updates
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # AI Assistant API
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

    # Health check
    location /health {
        proxy_pass http://airflow_backend/health;
        access_log off;
    }
}
NGINX_EOF

# Test nginx configuration
echo -e "${CYAN}  Testing nginx configuration...${NC}"
nginx -t || {
    echo -e "${RED}Nginx configuration test failed${NC}"
    exit 1
}

# Configure firewall
echo -e "${CYAN}  Configuring firewall...${NC}"
# Close direct access ports
firewall-cmd --permanent --remove-port=8888/tcp 2>/dev/null || true
firewall-cmd --permanent --remove-port=8080/tcp 2>/dev/null || true
# Open standard web ports
firewall-cmd --permanent --add-service=http
firewall-cmd --permanent --add-service=https
firewall-cmd --reload

# Enable and start nginx
echo -e "${CYAN}  Starting nginx service...${NC}"
systemctl enable nginx
systemctl restart nginx

# Verify nginx is running
if systemctl is-active --quiet nginx; then
    echo -e "${GREEN}  ✓ Nginx reverse proxy configured successfully${NC}"
else
    echo -e "${RED}  ✗ Nginx failed to start${NC}"
    exit 1
fi

# Step 4: Final verification
echo -e "${BLUE}[4/4] Verifying deployment...${NC}"
"$SCRIPT_DIR/airflow/deploy-airflow.sh" status

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          Qubinode Navigator Deployment Complete!              ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}🎯 Quick Links:${NC}"
echo -e "${GREEN}   • Airflow UI (via nginx): http://${SERVER_IP}/${NC}"
echo -e "   • AI Assistant API:         http://${SERVER_IP}/ai/"
echo -e "   • Health Check:             http://${SERVER_IP}/health"
echo -e ""
echo -e "${CYAN}🔐 Credentials:${NC}"
echo -e "   Username: admin"
echo -e "   Password: admin"
echo -e ""
echo -e "${YELLOW}🔒 Security:${NC}"
echo -e "   ✓ Direct ports 8888/8080 closed"
echo -e "   ✓ Access only through nginx (port 80/443)"
echo -e "   ✓ Ready for SSL/TLS configuration"
echo ""
echo -e "${CYAN}📚 Next Steps:${NC}"
echo -e "   1. Access Airflow UI and enable example DAGs"
echo -e "   2. Test kcli and virsh operators"
echo -e "   3. Chat with AI Assistant for guidance"
echo ""
echo -e "${CYAN}📖 Documentation:${NC}"
echo -e "   • airflow/README.md"
echo -e "   • airflow/TOOLS-AVAILABLE.md"
echo ""
