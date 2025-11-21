---
layout: default
title: "Modern Red Hat Demo System Deployment"
parent: Deployment Documentation
nav_order: 4
---

# 🚀 Modern Red Hat Demo System Deployment

Deploy to [Red Hat Product Demo System](https://connect.redhat.com/en/training/product-demo-system) using the **AI-enhanced one-shot deployment method**.

> **Architecture**: This deployment method implements [ADR-0031: Setup Script Modernization Strategy](../adrs/adr-0031-setup-script-modernization-strategy.md) with [ADR-0027: CPU-based AI Deployment Assistant](../adrs/adr-0027-cpu-based-ai-deployment-assistant-architecture.md) for Red Hat-specific guidance.

## 📋 **Prerequisites**

- **Platform**: Red Hat Product Demo System (Equinix Metal)
- **OS Support**: RHEL 9/10, CentOS Stream 9/10
- **Resources**: 8GB+ RAM, 50GB+ disk space
- **Access**: Root privileges, internet connectivity
- **Credentials**: Red Hat subscription and demo system access

## 🎯 **One-Shot Deployment (Recommended)**

### **Step 1: Initial Setup**

```bash
# SSH into your Red Hat Demo System server
ssh root@your-demo-server.opentlc.com

# Clone Qubinode Navigator
git clone https://github.com/tosin2013/qubinode_navigator.git
cd qubinode_navigator
```

### **Step 2: Pre-Deployment Cleanup**

```bash
# Run cleanup and backup script
./pre-deployment-cleanup.sh
```

### **Step 3: Configure Credentials**

Create `/tmp/config.yml` with your Red Hat credentials:

```bash
# Create credentials file (AI Assistant can help with this)
vi /tmp/config.yml
```

```yaml
# Red Hat Subscription Manager
rhsm_username: your_rh_username
rhsm_password: your_rh_password
rhsm_org: your_org_id
rhsm_activationkey: your_activation_key

# System Configuration
admin_user_password: your_lab_user_password
offline_token: your_offline_token
openshift_pull_secret: your_pull_secret

# Optional Services
automation_hub_offline_token: your_automation_hub_token
freeipa_server_admin_password: your_freeipa_password

# Remote Access
xrdp_remote_user: remoteuser
xrdp_remote_user_password: your_rdp_password

# Optional: AWS Integration
aws_access_key: your_aws_key  # For Route53 if needed
aws_secret_key: your_aws_secret
```

### **Step 4: Configure Environment**

```bash
# Copy and edit configuration
cp .env.example .env
vi .env
```

**Red Hat Demo System configuration:**
```bash
# =============================================================================
# RED HAT DEMO SYSTEM (EQUINIX) DEPLOYMENT CONFIGURATION
# =============================================================================

# Basic Configuration
QUBINODE_DOMAIN=sandbox000.opentlc.com  # Replace with your assigned domain
QUBINODE_ADMIN_USER=lab-user
QUBINODE_CLUSTER_NAME=rhel9-equinix-cluster
QUBINODE_DEPLOYMENT_MODE=production

# Red Hat Demo System Specific Settings
INVENTORY=rhel9-equinix
SSH_USER=lab-user
CICD_PIPELINE=true
ENV_USERNAME=lab-user

# Network Configuration (Auto-detected for Equinix)
FORWARDER=$(awk '/^nameserver/ {print $2}' /etc/resolv.conf | head -1)
INTERFACE=bond0
ACTIVE_BRIDGE=false

# Cloud Integration
USE_ROUTE53=true
EQUINIX_API_TOKEN=your_api_token  # Optional
EQUINIX_PROJECT_ID=your_project_id  # Optional

# AI Assistant (Recommended)
QUBINODE_ENABLE_AI_ASSISTANT=true
AI_ASSISTANT_PORT=8080

# Red Hat Subscription Integration
USE_HASHICORP_VAULT=false  # Or true for HCP Vault

# Optional: HashiCorp Cloud Platform Integration
# USE_HASHICORP_CLOUD=true
# HCP_CLIENT_ID=your_client_id
# HCP_CLIENT_SECRET=your_client_secret
# HCP_ORG_ID=your_org_id
# HCP_PROJECT_ID=your_project_id
# APP_NAME=rhel-demo-system
```

### **Step 5: Deploy with AI Assistant**

```bash
# Run the one-shot deployment
./deploy-qubinode.sh
```

The deployment will:
- ✅ **Automatically detect** Red Hat Demo System environment
- ✅ **Configure RHEL subscription** using your credentials
- ✅ **Set up networking** with Equinix-optimized settings
- ✅ **Deploy KVM hypervisor** with enterprise features
- ✅ **Configure Ansible Navigator** for Red Hat best practices
- ✅ **Set up kcli** with Red Hat image support
- ✅ **Start AI Assistant** for Red Hat-specific guidance

## 🤖 **AI Assistant Integration**

The AI Assistant provides Red Hat-specific expertise:

### **Red Hat Subscription Assistance**
```
🤖 AI: "Detected Red Hat Demo System environment. 
Configuring RHEL subscription with your credentials.
Applying Red Hat best practices for enterprise deployment..."
```

### **Equinix Metal Optimization**
```
🤖 AI: "Optimizing for Equinix Metal bare metal servers.
Configuring bond0 interface for network redundancy.
Applying enterprise-grade security settings..."
```

### **Interactive Red Hat Guidance**
```bash
# AI Assistant is available at:
http://your-server-ip:8080

# Ask Red Hat-specific questions:
# "How do I configure Red Hat Satellite integration?"
# "What are the best practices for RHEL 9 KVM deployment?"
# "How do I set up Red Hat Insights monitoring?"
```

## 🔧 **Advanced Red Hat Configuration**

### **Plugin Integration**

Leverages Red Hat-specific plugins:

```bash
# Red Hat Demo plugin (automatically applied)
# File: plugins/environments/redhat_demo_plugin.py
# Provides: RHEL subscription management, Equinix optimization

# OS-specific plugins (automatically detected)
# File: plugins/os/rhel9_plugin.py, plugins/os/rhel10_plugin.py
# Provides: RHEL version-specific optimizations
```

### **Enterprise Features**

```bash
# Advanced Red Hat settings in .env
RHEL_VERSION=9  # or 10
ENABLE_INSIGHTS=true
ENABLE_SATELLITE_INTEGRATION=false
ENABLE_ANSIBLE_AUTOMATION_PLATFORM=false

# Security and Compliance
QUBINODE_ENABLE_SECURITY_HARDENING=true
ENABLE_FIPS_MODE=false
ENABLE_SELINUX_ENFORCING=true

# Monitoring and Observability
ENABLE_COCKPIT=true
ENABLE_PROMETHEUS_MONITORING=true
```

## 📊 **Red Hat Demo System Verification**

After successful deployment:

```bash
# Check Red Hat subscription status
sudo subscription-manager status
sudo subscription-manager list --installed

# Check KVM hypervisor
sudo virsh list --all
sudo systemctl status libvirtd

# Check Red Hat services
sudo systemctl status cockpit
curl http://localhost:8080/health  # AI Assistant

# Access Cockpit Web Console
https://your-server.opentlc.com:9090
# Username: lab-user (or your configured admin user)
# Password: (from your /tmp/config.yml)
```

## 🖥️ **Remote Access Options**

### **Option 1: Cockpit Web Console**
```bash
# Access via web browser
https://your-server.opentlc.com:9090

# Features:
# - System monitoring and management
# - Virtual machine management
# - Log analysis and troubleshooting
# - Performance metrics
```

### **Option 2: RDP Access (if configured)**
```bash
# Connect via RDP client
Server: your-server.opentlc.com:3389
Username: remoteuser (from config.yml)
Password: (from config.yml)

# Or using xfreerdp
xfreerdp /v:your-server.opentlc.com:3389 /u:remoteuser
```

### **Option 3: SSH Access**
```bash
# Direct SSH access
ssh lab-user@your-server.opentlc.com

# Or with AI Assistant guidance
# Ask AI: "How do I configure SSH key-based authentication?"
```

## 🔄 **Migration from Legacy Method**

### **Legacy Process (Old Way)**
```bash
# OLD: Manual multi-step process
curl -OL https://raw.githubusercontent.com/tosin2013/qubinode_navigator/main/rhel9-linux-hypervisor.sh
# Manually create /tmp/config.yml
# Manually create notouch.env
# Run rhel9-linux-hypervisor.sh
# Often fails on first run, requires re-execution
# Manual troubleshooting for Red Hat-specific issues
```

### **Modern Process (New Way)**
```bash
# NEW: AI-enhanced one-shot deployment
git clone https://github.com/tosin2013/qubinode_navigator.git
cd qubinode_navigator
# Create /tmp/config.yml (AI can guide you)
cp .env.example .env
# Edit .env with Red Hat Demo System settings
./deploy-qubinode.sh
# AI Assistant provides Red Hat-specific help automatically
```

## 🆘 **Red Hat-Specific Troubleshooting**

### **AI-Powered Red Hat Support**

The AI Assistant automatically helps with:

1. **RHEL subscription issues**
2. **Equinix Metal network configuration**
3. **Red Hat package repository problems**
4. **SELinux policy conflicts**
5. **Red Hat Insights integration**
6. **Performance optimization for bare metal**

### **Common Red Hat Demo System Issues**

| Issue | AI-Assisted Solution | Manual Solution |
|-------|---------------------|-----------------|
| Subscription registration fails | AI guides through credential verification | `sudo subscription-manager register` |
| Network configuration on Equinix | AI applies Equinix-specific bond0 config | Manual network restart |
| Package installation failures | AI checks repos and suggests fixes | `sudo dnf clean all && dnf makecache` |
| SELinux denials | AI analyzes audit logs and suggests policies | `sudo sealert -a /var/log/audit/audit.log` |

### **Red Hat Support Integration**

```bash
# AI Assistant can help with Red Hat support cases
# Ask AI: "How do I collect sosreport for Red Hat support?"
# Ask AI: "What Red Hat documentation applies to my issue?"
# Ask AI: "How do I check Red Hat Insights recommendations?"
```

## 🎯 **Post-Deployment Red Hat Workflow**

### **Download Red Hat Images**
```bash
# Download RHEL images (AI-assisted)
sudo kcli download image rhel9
sudo kcli download image rhel8  # If needed for compatibility

# AI can guide you through image selection:
# "What RHEL images should I download for my use case?"
```

### **Red Hat Ecosystem Integration**
```bash
# Set up Red Hat Satellite (if available)
# Ask AI: "How do I register this system with Red Hat Satellite?"

# Configure Red Hat Insights
sudo insights-client --register

# Set up Ansible Automation Platform integration
# Ask AI: "How do I connect to Red Hat Ansible Automation Platform?"
```

### **Enterprise VM Deployment**
```bash
# Create enterprise-ready VMs
kcli create vm -P rhel9 -m 4096 -d 20 enterprise-vm1

# Apply Red Hat security baselines
# Ask AI: "How do I apply RHEL security baselines to my VMs?"
```

## 📚 **Red Hat Resources**

- **AI Assistant**: `http://your-server:8080` - Red Hat-specific guidance
- **Red Hat Customer Portal**: [https://access.redhat.com/](https://access.redhat.com/)
- **Red Hat Demo System**: [Product Demo System Portal](https://connect.redhat.com/en/training/product-demo-system)
- **RHEL Documentation**: [https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/)
- **Red Hat Insights**: [https://console.redhat.com/insights/](https://console.redhat.com/insights/)

## 🏢 **Enterprise Features**

Your Red Hat Demo System deployment includes:

- ✅ **Enterprise RHEL subscription** management
- ✅ **Red Hat certified** KVM hypervisor
- ✅ **Cockpit web console** for management
- ✅ **AI Assistant** with Red Hat expertise
- ✅ **Equinix Metal** optimized configuration
- ✅ **Enterprise security** hardening
- ✅ **Red Hat Insights** integration ready

---

## 🎉 **Success!**

Your Red Hat Demo System deployment is complete with enterprise-grade features and AI assistance!

**Need Red Hat-specific help?** Ask the AI Assistant at `http://your-server:8080` 🤖

**Enterprise Support**: The AI Assistant has been trained on Red Hat best practices and can provide enterprise-level guidance for your deployment.
