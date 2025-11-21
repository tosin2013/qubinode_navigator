---
layout: default
title: ADR-0035 Terminal-Centric Documentation
parent: Documentation & User Experience
grand_parent: Architectural Decision Records
nav_order: 0035
---

# ADR-0035: Terminal-Centric Documentation Strategy

## Status
Accepted

## Context
The Qubinode Navigator project needs comprehensive documentation that serves multiple user personas and use cases:

- New users deploying for the first time
- Experienced users extending existing deployments
- CI/CD pipeline integrators
- Contributors and developers
- Future Hugging Face showcase visitors

The documentation must work seamlessly with the terminal-based deployment architecture and AI Assistant integration, providing clear guidance that complements automated troubleshooting and post-deployment extension capabilities.

Current documentation is scattered across multiple files and lacks a cohesive user journey that integrates with the one-shot deployment approach and AI Assistant capabilities.

## Decision
We will implement a terminal-centric documentation strategy that provides comprehensive guidance for the complete user journey, from initial deployment through advanced infrastructure extension, with integrated AI Assistant interaction patterns.

### Core Documentation Principles:

1. **Terminal-First Approach**: All documentation assumes terminal-based interaction
2. **Progressive Disclosure**: Information organized by user experience level and use case
3. **AI Assistant Integration**: Documentation shows how to leverage AI for guidance
4. **Executable Examples**: All code examples are copy-pastable and tested
5. **Journey-Based Organization**: Content organized around user workflows, not technical components
6. **Future-Ready Structure**: Architecture supports Hugging Face showcase integration

### Implementation Details:

#### Documentation Architecture:
```
docs/
├── user-guides/
│   ├── quick-start.md              # New user 5-minute deployment
│   ├── deployment-guide.md         # Comprehensive deployment documentation
│   ├── ai-assistant-guide.md       # AI interaction patterns and examples
│   ├── post-deployment-guide.md    # Building on deployed infrastructure
│   └── troubleshooting-guide.md    # Common issues and AI-assisted resolution
├── reference/
│   ├── environment-variables.md    # Complete .env reference
│   ├── supported-platforms.md      # OS and cloud provider matrix
│   ├── api-reference.md           # AI Assistant API documentation
│   └── command-reference.md       # All available commands and scripts
├── examples/
│   ├── hetzner-deployment/        # Complete Hetzner deployment example
│   ├── local-development/         # Local development setup
│   ├── openshift-on-kvm/         # Post-deployment OpenShift example
│   └── ci-cd-integration/         # Pipeline integration examples
└── adrs/                          # Architectural Decision Records (existing)
```

#### User Journey Documentation:

1. **Discovery Phase**: Quick-start guide with single-command deployment
2. **Deployment Phase**: Comprehensive guide with AI Assistant integration
3. **Validation Phase**: Verification steps and troubleshooting with AI
4. **Extension Phase**: Building additional services on deployed infrastructure
5. **Maintenance Phase**: Updates, backups, and ongoing management

#### AI Assistant Integration Documentation:

##### During Deployment:
```markdown
## Getting Help During Deployment

The AI Assistant automatically provides guidance when errors occur - no manual intervention needed:

```bash
# Automatic AI assistance during deployment
./deploy-qubinode.sh

# If any step fails, you'll automatically see:
[ERROR] Failed to install packages
[AI ASSISTANT] Analyzing error and providing troubleshooting guidance...
╔══════════════════════════════════════════════════════════════╗
║                    AI ASSISTANT GUIDANCE                     ║
╚══════════════════════════════════════════════════════════════╝
The package installation failure is likely due to...
[Step-by-step resolution guidance]

For more help, visit: http://localhost:8080
```

No curl commands needed - the AI Assistant is seamlessly integrated!
```

##### Post-Deployment Extensions:
```markdown
## Building on Your Infrastructure

Ask the AI Assistant for guidance on next steps:

```bash
# Deploy OpenShift
curl -X POST -H "Content-Type: application/json" \
  -d '{"message": "How do I deploy OpenShift 4.14 on my KVM infrastructure?"}' \
  http://localhost:8080/chat

# Add monitoring
curl -X POST -H "Content-Type: application/json" \
  -d '{"message": "What monitoring solutions work well with this setup?"}' \
  http://localhost:8080/chat
```
```

#### Documentation Standards:

1. **Executable Code Blocks**: All examples must be copy-pastable and work
2. **Error Scenarios**: Document common failure modes and AI-assisted resolution
3. **Prerequisites**: Clear system requirements and validation steps
4. **Success Criteria**: How to verify each step completed successfully
5. **Next Steps**: Always provide clear progression paths

## Consequences

### Positive:
- **Reduced Onboarding Time**: New users can deploy successfully in minutes
- **Self-Service Support**: AI Assistant reduces need for human intervention
- **Consistent Experience**: Standardized documentation patterns across all guides
- **Extensibility Focus**: Clear guidance for building on deployed infrastructure
- **CI/CD Ready**: Documentation supports automated deployment scenarios
- **Community Showcase Ready**: Structure supports future Hugging Face integration

### Negative:
- **Maintenance Overhead**: Documentation must stay synchronized with code changes
- **AI Dependency**: Some guidance assumes AI Assistant availability
- **Terminal Assumption**: May not serve users preferring GUI interfaces

### Neutral:
- **Learning Curve**: Users must understand terminal and API interaction patterns
- **Content Volume**: Comprehensive documentation requires significant initial effort

## Implementation Status
- ⏳ Quick-start guide creation
- ⏳ AI Assistant interaction documentation
- ⏳ Post-deployment extension guides
- ⏳ Troubleshooting guide with AI integration
- ⏳ Reference documentation updates
- ⏳ Example scenarios and use cases

## Documentation Content Plan

### Phase 1: Core User Guides
1. **Quick-Start Guide** (5-minute deployment)
   - Single command: `./deploy-qubinode.sh`
   - Prerequisites check
   - Success validation
   - AI Assistant introduction

2. **AI Assistant Guide**
   - API interaction patterns
   - Common queries and responses
   - Troubleshooting workflows
   - Post-deployment guidance examples

### Phase 2: Extension Guides
1. **Post-Deployment Guide**
   - OpenShift deployment on KVM
   - Additional VM provisioning
   - Network and security configuration
   - Monitoring and logging setup

2. **Advanced Use Cases**
   - Multi-node deployments
   - Cloud provider integration
   - CI/CD pipeline setup
   - Backup and disaster recovery

### Phase 3: Reference Materials
1. **Complete API Reference**
2. **Environment Variable Documentation**
3. **Platform Compatibility Matrix**
4. **Troubleshooting Database**

## Quality Assurance

### Documentation Testing:
- All code examples tested on supported platforms
- AI Assistant interactions validated
- User journey walkthroughs with new users
- Regular updates based on user feedback

### Integration with Development:
- Documentation updates required for all feature changes
- ADR creation triggers documentation review
- AI Assistant training includes documentation content

## Related ADRs

### Dependencies (Required)
- ADR-0033: Terminal-Based One-Shot Deployment Architecture - Defines deployment workflow to document
- ADR-0034: AI Assistant Terminal Integration Strategy - Defines AI interaction patterns to document

### Integrates With
- ADR-0029: Documentation Strategy and Website Modernization - Provides broader documentation framework
- ADR-0027: CPU-Based AI Deployment Assistant Architecture - Documents AI capabilities and use cases
- ADR-0032: AI Assistant Community Distribution Strategy - Documents community distribution approach

### Supports
- ADR-0001: Container-First Execution Model - Documents containerized execution workflows
- ADR-0026: RHEL 10/CentOS 10 Platform Support Strategy - Documents modern OS support procedures

## Notes
This documentation strategy creates a comprehensive, AI-integrated user experience that guides users from initial deployment through advanced infrastructure extension. The terminal-centric approach ensures compatibility with the deployment architecture while preparing for future Hugging Face showcase integration.

The documentation serves as both user guidance and AI Assistant training material, creating a self-reinforcing knowledge system.
