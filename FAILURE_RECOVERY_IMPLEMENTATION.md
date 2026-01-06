# Failure Diagnosis & Recovery Agents - Implementation Guide

## Overview

This implementation adds intelligent failure diagnosis and recovery capabilities to Qubinode Navigator, enabling self-healing infrastructure and reduced manual intervention in CI/CD pipelines.

**Implements**: ADR-0069 (Agentic Failure Diagnosis and Recovery) with agentic patterns from [GitHub's blog on reliable AI workflows](https://github.blog/ai-and-ml/github-copilot/how-to-build-reliable-ai-workflows-with-agentic-primitives-and-context-engineering/)

______________________________________________________________________

## Architecture Overview

```
Failure Occurs
     │
     ▼
┌─────────────────────────────────┐
│  1. DiagnosticContext API       │ (core/base_plugin.py)
│  - Collect service health       │
│  - Get system resources         │
│  - Retrieve recent logs         │
│  - Map dependencies             │
└──────────────┬──────────────────┘
               │
     ┌─────────▼──────────┐
     │ 2. FailureAnalyzer │ (core/failure_analyzer.py)
     │                    │
     │ a) Pattern Match   │
     │    Known errors    │
     │ b) LLM Reasoning   │
     │    (PydanticAI)    │
     │ c) Service Corr.   │
     │    Unhealthy deps  │
     │ d) Resource Checks │
     │    CPU/Mem/Disk    │
     └─────────┬──────────┘
               │
     ┌─────────▼──────────────┐
     │ 3. RecoveryPlanner     │ (core/recovery_planner.py)
     │                        │
     │ Generate 3 Options:    │
     │ • Auto-Retry (low)     │
     │ • Manual Fix (med)     │
     │ • Escalate (high)      │
     │                        │
     │ Rank by confidence     │
     └─────────┬──────────────┘
               │
     ┌─────────▼──────────────┐
     │ 4. PluginManager       │ (core/plugin_manager.py)
     │    Recovery Hooks      │
     │                        │
     │ • diagnose_failure()   │
     │ • plan_recovery()      │
     │ • execute_recovery()   │
     │ • record_checkpoint()  │
     └─────────┬──────────────┘
               │
     ┌─────────▼──────────────┐
     │ 5. ShadowErrorDetector │ (ai-assistant/src/shadow_error_detector.py)
     │                        │
     │ Monitor for:           │
     │ • VM not created       │
     │ • Lineage missing      │
     │ • State mismatches     │
     └─────────┬──────────────┘
               │
     ┌─────────▼──────────────┐
     │ 6. GitHub Actions      │ (.github/workflows/failure-recovery-agent.yml)
     │    Orchestration       │
     │                        │
     │ Jobs:                  │
     │ • diagnose-failure     │
     │ • generate-plan        │
     │ • decide-action        │
     │ • report-status        │
     └────────────────────────┘
```

______________________________________________________________________

## Components Implemented

### 1. DiagnosticContext API (`core/base_plugin.py`)

**Purpose**: Unified interface for collecting failure diagnostic data

**Key Methods**:

- `get_plugin_logs(plugin_name, since_seconds=300)` → List\[Dict\]
- `get_service_status(service_name)` → Dict with active/pid/uptime
- `get_system_resources()` → Dict with CPU/memory/disk/network metrics
- `get_network_connectivity(target)` → Dict with reachability and latency

**Usage**:

```python
from core.base_plugin import DiagnosticContext

# Collect diagnostic context on failure
ctx = DiagnosticContext(
    plugin_name="HetznerDeploymentPlugin",
    failure_timestamp=datetime.now(),
    error_message="Failed to provision VM",
)

ctx.service_health = {
    "libvirtd": DiagnosticContext.get_service_status("libvirtd"),
    "podman": DiagnosticContext.get_service_status("podman"),
}
ctx.system_resources = DiagnosticContext.get_system_resources()
```

### 2. FailureAnalyzer (`core/failure_analyzer.py`)

**Purpose**: Classify root causes using pattern matching + optional LLM reasoning

**Root Cause Categories**:

- `VIRTUALIZATION` - KVM/virt-manager issues
- `NETWORK` - Connectivity, DNS, registry access
- `STORAGE` - Disk space, I/O failures
- `SERVICE_DEPENDENCY` - libvirtd, podman, airflow down
- `CREDENTIAL` - Auth/secrets issues
- `RESOURCE_EXHAUSTION` - CPU, memory, disk full
- `CONFIGURATION` - Invalid settings
- `TIMEOUT` - Operation exceeded time limit
- `STATE_MISMATCH` - System state inconsistency
- `UNKNOWN` - Unclassified

**Built-in Error Patterns** (extensible library):

- `virsh_001`: CPU virtualization not available
- `libvirt_001`: libvirtd not running
- `network_001`: Network unreachable
- `registry_001`: Container registry auth failed
- `disk_001`: No space left on device
- `credential_001`: Permission/auth denied
- `vault_001`: Vault service issues
- `timeout_001`: Operation timed out
- `airflow_001`: Airflow service/DAG issues
- `kcli_001`: VM operation failed

**LLM Integration** (Optional, via PydanticAI):

- Uses `gpt-4o` for advanced reasoning when confidence \< 70%
- Can be disabled by setting `use_llm=False`
- Falls back gracefully if API unavailable

**Usage**:

```python
from core.failure_analyzer import FailureAnalyzer, DiagnosticContext

analyzer = FailureAnalyzer(use_llm=True)
analysis = analyzer.analyze(diagnostic_ctx)

print(f"Root Cause: {analysis.root_cause.value}")
print(f"Confidence: {analysis.confidence:.0%}")
print(f"Recommended Actions:")
for action in analysis.recommended_actions:
    print(f"  - {action}")
```

### 3. RecoveryPlanner (`core/recovery_planner.py`)

**Purpose**: Generate multiple recovery options and optionally create GitHub issues

**Recovery Options**:

1. **RETRY** (priority 1)

   - Re-execute with checkpoint recovery
   - Adjust timeout/parameters based on failure type
   - Low risk if infrastructure is healthy

1. **MANUAL_FIX** (priority 2)

   - Suggest diagnostic commands (systemctl, df, ping, etc.)
   - Specific steps based on root cause
   - Medium risk, requires human execution

1. **ESCALATE** (priority 3)

   - Create GitHub issue with full diagnostic context
   - Low risk, enables human review
   - Supports async resolution

**Features**:

- Ranks options by priority and confidence
- Generates diagnostic commands matched to root cause
- Creates detailed GitHub issues with context
- Supports rollback procedures
- Idempotent recovery execution

**Usage**:

```python
from core.recovery_planner import RecoveryPlanner

planner = RecoveryPlanner(
    github_token=os.getenv("GITHUB_TOKEN"),
    github_repo="Qubinode/qubinode_navigator",
)

plan = planner.plan_recovery(failure_analysis)
print(f"Recommended: {plan.recommended_option.action_type.value}")

# Execute if safe
if plan.recommended_option.confidence > 0.85:
    success = planner.execute_recovery(plan, plan.recommended_option)
```

### 4. PluginManager Recovery Hooks (`core/plugin_manager.py`)

**Purpose**: Integrate failure diagnosis and recovery into plugin orchestration

**New Methods**:

- `diagnose_failure(plugin_name, failure_message, context)` → FailureAnalysis
- `plan_recovery(failure_analysis, plugin_name)` → RecoveryPlan
- `execute_recovery(recovery_plan, context)` → bool
- `record_checkpoint(plugin_name, state)` → None
- `register_recovery_handler(plugin_name, handler)` → None
- `set_auto_recovery_enabled(enabled)` → None
- `set_approval_callback(callback)` → None

**New Fields**:

- `_failure_analyzer`: FailureAnalyzer instance
- `_recovery_planner`: RecoveryPlanner instance
- `_plugin_checkpoints`: Dict of state snapshots
- `_recovery_handlers`: Custom recovery handlers per plugin
- `_auto_recovery_enabled`: Flag to enable/disable auto-recovery
- `_approval_callback`: Optional approval gate

**Usage**:

```python
from core.plugin_manager import PluginManager

manager = PluginManager()
manager.initialize()

# Enable auto-recovery for this session
manager.set_auto_recovery_enabled(True)

# Set approval callback for interactive mode
def approve_recovery(plan):
    print(f"Execute recovery: {plan.recommended_option.action_type.value}? (y/n)")
    return input().lower() == 'y'

manager.set_approval_callback(approve_recovery)

# Execute plugin (auto-recovery on failure)
result = manager.execute_plugin("HetznerDeploymentPlugin", context)
```

### 5. ShadowErrorDetector (`ai-assistant/src/shadow_error_detector.py`)

**Purpose**: Detect failures that don't immediately manifest (ADR-0067)

**Detection Types**:

- `vm_not_created`: DAG succeeds but VM not in libvirt
- `lineage_missing`: DAG succeeds but no Marquez lineage recorded
- `state_mismatch`: DAG marked success but contains failed tasks
- `kcli_check_failed`: Cannot verify VM creation

**Mechanisms**:

1. Correlates Airflow DAG execution with actual resource state
1. Checks Marquez for missing lineage
1. Queries libvirt/kcli for VM presence
1. Analyzes task instance states for inconsistencies

**Usage**:

```python
from ai_assistant.src.shadow_error_detector import ShadowErrorDetector
import asyncio

detector = ShadowErrorDetector()

# One-time scan
errors = asyncio.run(detector.scan_for_shadow_errors())

# Continuous monitoring
asyncio.run(detector.monitor_continuously(interval_seconds=300))
```

### 6. GitHub Actions Workflow (`.github/workflows/failure-recovery-agent.yml`)

**Purpose**: Orchestrate failure diagnosis and recovery in CI/CD

**Jobs**:

1. `diagnose-failure`: Run FailureAnalyzer with full context
1. `generate-recovery-plan`: Create recovery options and markdown
1. `decide-recovery-action`: Evaluate confidence and decide action
1. `report-status`: Summarize results and create issue if needed

**Triggering**:

From E2E test on failure:

```yaml
- name: Trigger failure recovery
  if: failure()
  uses: ./.github/workflows/failure-recovery-agent.yml
  with:
    failed_job: "E2E Integration Test"
    failure_message: ${{ steps.test.outputs.error }}
    enable_auto_recovery: true
```

Manual trigger:

```bash
gh workflow run failure-recovery-agent.yml \
  -f failed_job="E2E Integration Test" \
  -f failure_message="Timeout waiting for Airflow" \
  -f enable_auto_recovery=true
```

______________________________________________________________________

## Configuration & Environment Variables

### FailureAnalyzer Options

```python
# Use LLM for advanced reasoning (requires OPENROUTER_API_KEY or OPENAI_API_KEY)
analyzer = FailureAnalyzer(use_llm=True)

# Disable LLM (pattern matching only)
analyzer = FailureAnalyzer(use_llm=False)
```

### RecoveryPlanner Options

```python
# With GitHub integration (creates issues on escalation)
planner = RecoveryPlanner(
    github_token=os.getenv("GITHUB_TOKEN"),
    github_repo=os.getenv("GITHUB_REPOSITORY"),
)

# Without GitHub (no escalation issues)
planner = RecoveryPlanner()
```

### PluginManager Options

```python
manager = PluginManager()

# Enable automatic recovery on plugin failure
manager.set_auto_recovery_enabled(True)

# Disable auto-recovery (manual decision required)
manager.set_auto_recovery_enabled(False)

# Require approval before executing recovery
manager.set_approval_callback(lambda plan: user_approves(plan))
```

______________________________________________________________________

## Usage Examples

### Example 1: Diagnose a Failure

```bash
python3 failure_recovery_cli.py diagnose \
  --plugin HetznerDeploymentPlugin \
  --error "Failed to connect to registry.redhat.io" \
  --output /tmp/analysis.json
```

**Output**:

```
============================================================
Failure Diagnosis: HetznerDeploymentPlugin
============================================================

Root Cause: network
Confidence: 80%
Severity: high
Description: Cannot reach container registry or authentication failed

Pattern Matches: registry_001
Affected Services: podman, container_runtime

Recommended Actions:
  1. Check registry credentials and network access to registry
  2. Test registry access: curl -I https://registry.redhat.io

[OK] Analysis saved to /tmp/analysis.json
```

### Example 2: Create Recovery Plan

```bash
python3 failure_recovery_cli.py plan \
  --analysis-file /tmp/analysis.json \
  --output /tmp/recovery_plan.md
```

**Output**:

```
============================================================
Recovery Planning
============================================================

Recovery Options for: HetznerDeploymentPlugin

1. RETRY
   Priority: 1/3
   Confidence: 85%
   Risk: low
   Duration: 300s
   Description: Re-execute the failed plugin with checkpoint recovery

   Steps:
     - Load last checkpoint (system state snapshot)
     - Re-execute HetznerDeploymentPlugin plugin
     - Compare state with desired state
     - Verify plugin health status

2. MANUAL_FIX
   Priority: 2/3
   Confidence: 75%
   Risk: medium
   Duration: 600s
   Description: Execute manual diagnostic and fix steps

   Steps:
     - Check registry credentials: cat ~/.docker/config.json
     - Test registry access: curl -I https://registry.redhat.io
     - Check firewall: sudo firewall-cmd --list-all

3. ESCALATE
   Priority: 3/3
   Confidence: 100%
   Risk: low
   Duration: 3600s
   Description: Create GitHub issue for human review

   Steps:
     - Create GitHub issue with failure analysis
     - Include diagnostic context and service health
     - Assign to on-call engineer

[OK] Recovery plan saved to /tmp/recovery_plan.md
```

### Example 3: Integrate with Plugin Manager

```python
from core.plugin_manager import PluginManager
from core.base_plugin import ExecutionContext

manager = PluginManager(["plugins"])
manager.initialize()

# Enable auto-recovery
manager.set_auto_recovery_enabled(True)

# Create execution context
context = ExecutionContext(
    inventory="localhost",
    environment="production",
    config={},
    variables={},
)

# Execute plugin (will auto-recover on failure)
result = manager.execute_plugin("HetznerDeploymentPlugin", context)

if result.status.value == "completed":
    print("✓ Plugin executed successfully")
elif result.status.value == "failed":
    print("✗ Plugin failed after recovery attempts")
```

### Example 4: Detect Shadow Errors

```bash
python3 failure_recovery_cli.py detect-shadows --scan-hours 1
```

**Output**:

```
============================================================
Shadow Error Detection
============================================================

[INFO] Scanning for shadow errors (last 1 hour(s))...

[WARN] Found 2 shadow errors:

- vm_not_created: DAG freeipa_deployment succeeded but VM freeipa not found
  DAG: freeipa_deployment
  Confidence: 95%

- lineage_missing: No lineage recorded for ocp_agent_deployment
  DAG: ocp_agent_deployment
  Confidence: 80%

[OK] Available in detector.shadow_errors
```

______________________________________________________________________

## Error Pattern Library

The built-in patterns can be extended:

```python
from core.failure_analyzer import FailureAnalyzer, KnownErrorPattern, RootCauseCategory, FailureSeverity

analyzer = FailureAnalyzer()

# Add custom pattern
custom_pattern = KnownErrorPattern(
    pattern_id="custom_001",
    regex=r"my custom error message",
    root_cause=RootCauseCategory.CONFIGURATION,
    description="Custom configuration issue",
    severity=FailureSeverity.MEDIUM,
    services_affected=["my_service"],
    recovery_hint="Check /etc/my_service.conf for invalid settings",
)

analyzer._patterns.append(custom_pattern)
```

______________________________________________________________________

## Integration with Existing Systems

### With ApprovalGateManager

```python
from core.plugin_manager import PluginManager
from core.approval_gate_manager import ApprovalGateManager

manager = PluginManager()
approvals = ApprovalGateManager()

# Require approval for recovery
def approval_callback(plan):
    return approvals.should_approve(
        stage="recovery",
        risk_level=plan.recommended_option.risk_level,
        plugin=plan.failed_plugin,
    )

manager.set_approval_callback(approval_callback)
```

### With EventSystem

```python
# Events are automatically emitted:
# - plugin_failure_diagnosed
# - recovery_plan_created
# - recovery_executed

event_system.subscribe("recovery_executed", lambda data:
    print(f"Recovery {data['action_type']} for {data['plugin_name']}")
)
```

### With LogAnalyzer

```python
from core.log_analyzer import LogAnalyzer
from core.failure_analyzer import FailureAnalyzer

log_analyzer = LogAnalyzer()
failure_analyzer = FailureAnalyzer()

# Use LogAnalyzer's error patterns as input
error_patterns = log_analyzer.analyze_logs(deployment_session)
for pattern in error_patterns:
    # Feed to failure analyzer
    print(f"Known error: {pattern.description}")
```

______________________________________________________________________

## Testing

### Unit Tests

```bash
python3 -m pytest tests/unit/test_failure_analyzer.py -v
python3 -m pytest tests/unit/test_recovery_planner.py -v
```

### Integration Tests

```bash
python3 -m pytest tests/integration/test_plugin_recovery.py -v
```

### Manual Testing

```bash
# Test failure analyzer
python3 failure_recovery_cli.py diagnose \
  --plugin TestPlugin \
  --error "libvirtd is not running"

# Test recovery planner
python3 failure_recovery_cli.py plan \
  --analysis-file /tmp/analysis.json

# Test shadow error detection
python3 failure_recovery_cli.py detect-shadows
```

______________________________________________________________________

## Performance Characteristics

- **FailureAnalyzer**: ~200ms (pattern matching), +500ms (LLM reasoning)
- **RecoveryPlanner**: ~100ms (plan generation)
- **PluginManager recovery**: ~1-5 min (depending on recovery option)
- **ShadowErrorDetector**: ~2 seconds per DAG run (async)
- **Overall diagnostic time**: \<1 second (no LLM)

______________________________________________________________________

## Security Considerations

1. **Credentials**: GitHub tokens, API keys handled via environment variables
1. **Shell commands**: Executed with restricted permissions, input validated
1. **File access**: Respects system permissions, no privilege escalation
1. **Network**: HTTPS only for remote APIs, timeout protections

______________________________________________________________________

## Future Enhancements

1. **Machine Learning**: Train models on historical failures for better classification
1. **Adaptive Timeouts**: Adjust timeout values based on system load
1. **Predictive Recovery**: Proactively identify likely failures before they occur
1. **Custom Strategies**: Per-plugin custom recovery handlers
1. **Slack/PagerDuty Integration**: Real-time alerts and escalations
1. **Multi-Agent Coordination**: Agents collaboratively solving complex failures

______________________________________________________________________

## Files Modified/Created

### Created

- `core/failure_analyzer.py` (430 lines)
- `core/recovery_planner.py` (370 lines)
- `ai-assistant/src/shadow_error_detector.py` (400 lines)
- `.github/workflows/failure-recovery-agent.yml` (280 lines)
- `failure_recovery_cli.py` (280 lines)

### Modified

- `core/base_plugin.py` (added DiagnosticContext class, 200+ lines)
- `core/plugin_manager.py` (added recovery hooks, 150+ lines)

**Total Lines Added**: ~2,100 lines of production code

______________________________________________________________________

## References

- [GitHub Blog: Reliable AI Workflows with Agentic Primitives](https://github.blog/ai-and-ml/github-copilot/how-to-build-reliable-ai-workflows-with-agentic-primitives-and-context-engineering/)
- ADR-0028: Plugin Architecture
- ADR-0063: PydanticAI Orchestrator
- ADR-0066: Observer Agent for DAG Monitoring
- ADR-0067: Shadow Error Detection
- ADR-0069: Agentic Failure Diagnosis and Recovery

______________________________________________________________________

## Contact & Support

For issues or improvements to the failure recovery system:

- Create an issue: https://github.com/Qubinode/qubinode_navigator/issues
- Tag: `failure-diagnosis`, `agentic-recovery`
- Include: failure logs, diagnostic output, system state
