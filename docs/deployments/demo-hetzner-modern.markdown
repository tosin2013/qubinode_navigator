---
layout: default
title: "Modern Hetzner Cloud Deployment"
parent: Deployment Documentation
nav_order: 3
---

# 🚀 Modern Hetzner Cloud Deployment

Deploy to [Hetzner Cloud](https://www.hetzner.com/) using the **AI-enhanced one-shot deployment method**.

> **Architecture**: This deployment method implements [ADR-0031: Setup Script Modernization Strategy](../adrs/adr-0031-setup-script-modernization-strategy.md) and leverages [ADR-0028: Modular Plugin Framework](../adrs/adr-0028-modular-plugin-framework-for-extensibility.md) for intelligent deployment automation.

## 📋 **Prerequisites**

- **OS Support**: Rocky Linux 9, RHEL 9/10, CentOS Stream 9/10
- **Resources**: 8GB+ RAM, 50GB+ disk space
- **Access**: Root privileges, internet connectivity
- **Hardware**: VT-x/AMD-V virtualization support

## 🎯 **One-Shot Deployment (Recommended)**

### **Step 1: Initial Setup**

```bash
# SSH into your Hetzner server as root
ssh root@your-hetzner-server.com

# Create lab-user (if needed)
curl -OL https://gist.githubusercontent.com/tosin2013/385054f345ff7129df6167631156fa2a/raw/b67866c8d0ec220c393ea83d2c7056f33c472e65/configure-sudo-user.sh
chmod +x configure-sudo-user.sh
./configure-sudo-user.sh lab-user

# Clone Qubinode Navigator
git clone https://github.com/tosin2013/qubinode_navigator.git
cd qubinode_navigator
```

### **Step 2: Pre-Deployment Cleanup**

```bash
# Run cleanup and backup script
./pre-deployment-cleanup.sh
```

### **Step 3: Configure Environment**

```bash
# Copy and edit configuration
cp .env.example .env
vi .env
```

**Hetzner-specific configuration:**
```bash
# =============================================================================
# HETZNER CLOUD DEPLOYMENT CONFIGURATION
# =============================================================================

# Basic Configuration
QUBINODE_DOMAIN=qubinodelab.io
QUBINODE_ADMIN_USER=lab-user
QUBINODE_CLUSTER_NAME=hetzner-cluster
QUBINODE_DEPLOYMENT_MODE=production

# Hetzner-Specific Settings
INVENTORY=hetzner
SSH_USER=lab-user
CICD_PIPELINE=true
ENV_USERNAME=lab-user

# Network Configuration
FORWARDER=1.1.1.1
INTERFACE=bond0
ACTIVE_BRIDGE=false

# Cloud Integration
USE_ROUTE53=true
HETZNER_TOKEN=your_hetzner_token

# AI Assistant (Recommended)
QUBINODE_ENABLE_AI_ASSISTANT=true
AI_ASSISTANT_PORT=8080

# Optional: HashiCorp Vault Integration
USE_HASHICORP_VAULT=false
# USE_HASHICORP_CLOUD=true
# HCP_CLIENT_ID=your_client_id
# HCP_CLIENT_SECRET=your_client_secret
```

### **Step 4: Deploy with AI Assistant**

```bash
# Run the one-shot deployment
./deploy-qubinode.sh
```

The deployment will:
- ✅ **Automatically detect** Hetzner Cloud environment
- ✅ **Configure OS packages** for your RHEL-based system
- ✅ **Set up networking** with Hetzner-optimized settings
- ✅ **Deploy KVM hypervisor** with libvirt
- ✅ **Configure Ansible Navigator** for container-first execution
- ✅ **Set up kcli** for VM management
- ✅ **Start AI Assistant** for real-time help

## 🤖 **AI Assistant Integration**

During deployment, the **AI Assistant** provides:

### **Real-Time Troubleshooting**
- **Automatic error detection** and context-aware solutions
- **Configuration guidance** for Hetzner-specific settings
- **Network troubleshooting** for bond0 interface issues
- **Performance optimization** recommendations

### **Interactive Help**
```bash
# AI Assistant is available at:
http://your-server-ip:8080

# Or ask for help during deployment:
# The script automatically provides AI assistance when errors occur
```

### **Common AI-Assisted Solutions**

**Network Configuration Issues:**
```
🤖 AI: "Detected bond0 interface configuration issue. 
Hetzner Cloud typically uses bond0 for network redundancy. 
Checking interface status and applying Hetzner-specific fixes..."
```

**Storage Configuration:**
```
🤖 AI: "Optimizing storage for Hetzner Cloud SSD configuration.
Recommended LVM setup for KVM guests detected and applied."
```

## 🔧 **Advanced Configuration**

### **Plugin Integration**

The deployment leverages plugins from `docs/plugins/` for enhanced functionality:

```bash
# Cloud provider plugin (automatically detected)
# File: plugins/cloud/hetzner_plugin.py
# Provides: Hetzner-specific network and storage optimization

# Environment plugin (automatically applied)  
# File: plugins/environments/hetzner_deployment_plugin.py
# Provides: Hetzner Cloud deployment patterns and best practices
```

### **Custom Configuration Options**

```bash
# Advanced Hetzner settings in .env
HETZNER_DATACENTER=nbg1-dc3
HETZNER_SERVER_TYPE=cx41
HETZNER_NETWORK_ZONE=eu-central

# Storage optimization
QUBINODE_STORAGE_SIZE=200Gi
QUBINODE_WORKER_NODES=3

# Security hardening
QUBINODE_ENABLE_SECURITY_HARDENING=true
QUBINODE_ENABLE_NETWORK_POLICIES=true
```

## 📊 **Deployment Verification**

After successful deployment:

```bash
# Check KVM hypervisor
sudo virsh list --all
sudo systemctl status libvirtd

# Check AI Assistant
curl http://localhost:8080/health

# Check kcli
kcli list profiles
kcli list images

# Access Cockpit (if enabled)
https://your-server-ip:9090
```

## 🔄 **Migration from Legacy Method**

### **Legacy Process (Old Way)**
```bash
# OLD: Manual multi-step process
curl -OL https://raw.githubusercontent.com/tosin2013/qubinode_navigator/main/rocky-linux-hetzner.sh
# Create notouch.env manually
# Create /tmp/config.yml manually  
# Run rocky-linux-hetzner.sh
# Manual troubleshooting
```

### **Modern Process (New Way)**
```bash
# NEW: AI-enhanced one-shot deployment
git clone https://github.com/tosin2013/qubinode_navigator.git
cd qubinode_navigator
cp .env.example .env
# Edit .env with Hetzner settings
./deploy-qubinode.sh
# AI Assistant provides automatic help
```

## 🆘 **Troubleshooting**

### **AI-Powered Troubleshooting**

The AI Assistant automatically helps with:

1. **Hetzner-specific network issues**
2. **Bond0 interface configuration**
3. **Storage optimization for SSD**
4. **Firewall configuration for Hetzner Cloud**
5. **Performance tuning recommendations**

### **Manual Troubleshooting**

If AI Assistant is unavailable:

```bash
# Check deployment logs
tail -f /tmp/qubinode-deployment-*.log

# Check system resources
free -h && df -h

# Verify virtualization support
grep -E '(vmx|svm)' /proc/cpuinfo

# Check network configuration
ip addr show bond0
```

### **Common Issues & Solutions**

| Issue | AI-Assisted Solution | Manual Solution |
|-------|---------------------|-----------------|
| Bond0 not configured | AI detects and applies Hetzner network config | `sudo systemctl restart networking` |
| Storage optimization | AI applies SSD-optimized LVM settings | Manual LVM configuration |
| Firewall blocking | AI configures Hetzner Cloud firewall rules | `sudo firewall-cmd --list-all` |

## 🎯 **Next Steps**

After successful deployment:

1. **VM Management**: Use `kcli` to create and manage VMs
2. **Monitoring**: Access Cockpit at `https://your-server:9090`
3. **AI Assistance**: Continue using AI Assistant for operations
4. **Scaling**: Add more nodes or resources as needed

### **Recommended Post-Deployment Actions**

```bash
# Download VM images
sudo kcli download image rhel9
sudo kcli download image rocky9

# Create your first VM
kcli create vm -P rhel9 myvm

# Set up monitoring (AI-assisted)
# Ask AI Assistant: "How do I set up monitoring for my Hetzner deployment?"
```

## 📚 **Additional Resources**

- **AI Assistant**: `http://your-server:8080` - Interactive help and guidance
- **Hetzner Cloud Docs**: [https://docs.hetzner.com/](https://docs.hetzner.com/)
- **kcli Documentation**: [https://kcli.readthedocs.io/](https://kcli.readthedocs.io/)
- **Qubinode Navigator**: [GitHub Repository](https://github.com/tosin2013/qubinode_navigator)

---

## 🎉 **Success!**

Your Hetzner Cloud deployment is complete with:
- ✅ **Modern RHEL-based hypervisor** ready for workloads
- ✅ **AI Assistant** available for ongoing support  
- ✅ **Optimized configuration** for Hetzner Cloud
- ✅ **Enterprise-ready** KVM virtualization platform

**Need help?** Ask the AI Assistant at `http://your-server:8080` 🤖
