---
layout: default
title: ADR-0034 AI Terminal Integration
parent: Architecture & Design
grand_parent: Architectural Decision Records
nav_order: 0034
---

# ADR-0034: AI Assistant Terminal Integration Strategy

## Status
Accepted

## Context
The Qubinode Navigator deployment process can encounter various issues across different operating systems, cloud providers, and hardware configurations. Users need intelligent troubleshooting assistance that can:

- Provide contextual guidance during deployment failures
- Analyze system-specific error conditions
- Offer post-deployment extension recommendations
- Guide users through building on top of deployed infrastructure
- Work entirely through terminal/API interactions
- Support future integration with Hugging Face for broader AI capabilities

The current deployment scripts lack intelligent error analysis and user guidance, leading to users getting stuck on deployment issues without clear resolution paths.

## Decision
We will integrate a containerized AI Assistant that provides terminal-based deployment support through API interactions, with the capability to guide users both during deployment troubleshooting and post-deployment infrastructure extension.

### Core Integration Principles:

1. **Containerized Deployment**: AI Assistant runs as a Podman container (quay.io/takinosh/qubinode-ai-assistant)
2. **API-Based Interaction**: All interactions through HTTP API calls (curl) from terminal
3. **Non-Blocking Integration**: Deployment continues even if AI Assistant fails to start
4. **Contextual Awareness**: AI receives deployment context (OS, errors, system info) for targeted guidance
5. **Post-Deployment Guidance**: AI helps users extend and build upon deployed infrastructure
6. **Future Extensibility**: Architecture supports future Hugging Face integration

### Implementation Details:

#### AI Assistant Container Integration:
```bash
# Container Management
podman pull quay.io/takinosh/qubinode-ai-assistant:latest
podman run -d --name qubinode-ai-assistant \
  -p 8080:8080 \
  -e DEPLOYMENT_MODE=${QUBINODE_DEPLOYMENT_MODE} \
  -e LOG_LEVEL=INFO \
  quay.io/takinosh/qubinode-ai-assistant:latest
```

#### Automatic AI Integration Pattern:
```bash
# AI Assistant automatically activated on errors
[ERROR] Failed to install RHEL 10 packages
[AI ASSISTANT] Analyzing error and providing troubleshooting guidance...
╔══════════════════════════════════════════════════════════════╗
║                    AI ASSISTANT GUIDANCE                     ║
╚══════════════════════════════════════════════════════════════╝
[Contextual troubleshooting advice appears here automatically]

For more help, visit: http://localhost:8080

# Manual health check (if needed)
curl -s http://localhost:8080/health
```

#### Contextual Error Reporting:
```json
{
  "deployment_context": {
    "os_type": "centos",
    "os_version": "10", 
    "deployment_mode": "production",
    "cluster_name": "qubinode",
    "domain": "example.com"
  },
  "error_context": "package_installation",
  "error_message": "dnf install failed for ansible-core",
  "system_info": {
    "memory_gb": 16,
    "disk_space_gb": 100,
    "timestamp": "2025-11-11T05:00:00Z"
  }
}
```

#### Integration Points in deploy-qubinode.sh:

1. **Startup Phase**: Non-blocking AI Assistant container startup
2. **Error Handling**: Automatic AI consultation on deployment failures
3. **Completion Phase**: AI guidance for next steps and extensions
4. **Manual Consultation**: Users can query AI Assistant directly via curl

#### Post-Deployment Guidance Capabilities:
- OpenShift deployment on KVM infrastructure
- Additional VM provisioning and management
- Network configuration and security hardening
- Monitoring and logging setup
- Backup and disaster recovery planning

## Consequences

### Positive:
- **Intelligent Troubleshooting**: Context-aware error analysis and resolution guidance
- **Reduced Support Burden**: AI handles common deployment issues automatically
- **User Empowerment**: Guides users to extend infrastructure independently
- **Consistent Experience**: Standardized troubleshooting approach across all deployments
- **Scalable Support**: AI can handle multiple concurrent user queries
- **Future Ready**: Architecture supports advanced AI model integration

### Negative:
- **Container Dependency**: Requires Podman and container image availability
- **Network Requirement**: AI Assistant needs internet access for container pull
- **Resource Overhead**: Additional memory and CPU usage for AI container
- **API Dependency**: Terminal interactions depend on HTTP API availability

### Neutral:
- **Optional Integration**: Deployment continues without AI Assistant if unavailable
- **Learning Curve**: Users need to understand API interaction patterns
- **Model Limitations**: AI responses limited by training data and model capabilities

## Implementation Status
- ✅ AI Assistant container available at quay.io/takinosh/qubinode-ai-assistant
- ✅ Container integration in deploy-qubinode.sh (lines 317-433)
- ✅ Error context generation and API interaction patterns
- ✅ Health check and startup validation
- ⏳ Post-deployment guidance documentation
- ⏳ Terminal interaction pattern documentation
- ⏳ Hugging Face integration planning

## Terminal Interaction Examples

### During Deployment Error:
```bash
# Automatic AI consultation (built into deploy-qubinode.sh)
[ERROR] Failed to install RHEL 10 packages
[AI ASSISTANT] Analyzing error and providing troubleshooting guidance...
╔══════════════════════════════════════════════════════════════╗
║                    AI ASSISTANT GUIDANCE                     ║
╚══════════════════════════════════════════════════════════════╝
The package installation failure on RHEL 10 is likely due to...
[Detailed troubleshooting steps provided]

For more help, visit: http://localhost:8080
```

### Manual Post-Deployment Consultation:
```bash
# AI Assistant URL provided at deployment completion
# Users can visit http://localhost:8080 in browser or use API
curl -X POST -H "Content-Type: application/json" \
  -d '{"message": "I have successfully deployed Qubinode Navigator. How do I deploy OpenShift on top of this KVM infrastructure?"}' \
  http://localhost:8080/chat

# AI provides step-by-step OpenShift deployment guidance
```

## Related ADRs

### Dependencies (Required)
- ADR-0027: CPU-Based AI Deployment Assistant Architecture - Defines AI Assistant foundation and capabilities
- ADR-0032: AI Assistant Community Distribution Strategy - Provides container distribution and CI/CD pipeline
- ADR-0033: Terminal-Based One-Shot Deployment Architecture - Provides deployment orchestration framework

### Integrates With
- ADR-0001: Container-First Execution Model - Uses containerized AI Assistant deployment
- ADR-0028: Modular Plugin Framework - AI Assistant available as plugin for other components
- ADR-0035: Terminal-Centric Documentation Strategy - Defines user interaction documentation patterns

## Notes
This ADR establishes the AI Assistant as an integral part of the deployment experience while maintaining system functionality when AI is unavailable. The terminal-based API interaction pattern ensures compatibility with CI/CD pipelines and remote deployment scenarios.

The architecture is designed to support future enhancements including Hugging Face integration for advanced AI capabilities and community showcase features.
