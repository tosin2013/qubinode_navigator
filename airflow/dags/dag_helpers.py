"""
DAG Helper Functions for ocp4-disconnected-helper
Provides reusable utilities for:
- VM cleanup on failure
- Clear error reporting with file paths
- Credential management via Airflow Variables
- Validation helpers

These helpers implement CI/CD-style patterns:
- Idempotent operations
- Self-healing (automatic cleanup)
- Clear error messages pointing to specific files
"""

import os
import json
import subprocess
from datetime import datetime
from typing import Optional, Dict, List, Any

# =============================================================================
# Error Reporting Helpers
# =============================================================================

def format_config_error(
    config_file: str,
    field: str,
    error_msg: str,
    suggested_fix: Optional[str] = None,
    related_dag: Optional[str] = None
) -> str:
    """
    Format a configuration error with actionable information.
    
    Args:
        config_file: Full path to the config file with the error
        field: The field/key that has the issue
        error_msg: Description of what's wrong
        suggested_fix: Optional command or steps to fix
        related_dag: Optional DAG that can fix this issue
    
    Returns:
        Formatted error message string
    """
    separator = "=" * 60
    
    message = f"""
{separator}
CONFIGURATION ERROR
{separator}

File:  {config_file}
Field: {field}
Error: {error_msg}

"""
    
    if suggested_fix:
        message += f"""To fix manually:
{suggested_fix}

"""
    
    if related_dag:
        message += f"""Or run this DAG to fix automatically:
  airflow dags trigger {related_dag}

"""
    
    message += f"""After fixing, retrigger this DAG to continue.
{separator}
"""
    return message


def format_validation_error(
    check_name: str,
    expected: str,
    actual: str,
    config_file: Optional[str] = None,
    fix_command: Optional[str] = None
) -> str:
    """
    Format a validation error with expected vs actual values.
    """
    separator = "-" * 60
    
    message = f"""
{separator}
VALIDATION FAILED: {check_name}
{separator}
Expected: {expected}
Actual:   {actual}
"""
    
    if config_file:
        message += f"Config:   {config_file}\n"
    
    if fix_command:
        message += f"\nTo fix:\n  {fix_command}\n"
    
    message += separator + "\n"
    return message


def format_success_report(
    operation: str,
    details: Dict[str, Any],
    next_steps: Optional[List[str]] = None
) -> str:
    """
    Format a success report with details and next steps.
    """
    separator = "=" * 60
    
    message = f"""
{separator}
SUCCESS: {operation}
{separator}
Timestamp: {datetime.now().isoformat()}

Details:
"""
    
    for key, value in details.items():
        message += f"  {key}: {value}\n"
    
    if next_steps:
        message += "\nNext Steps:\n"
        for i, step in enumerate(next_steps, 1):
            message += f"  {i}. {step}\n"
    
    message += separator + "\n"
    return message


# =============================================================================
# VM Cleanup Helpers (Bash Commands)
# =============================================================================

def get_vm_cleanup_command(vm_name: str, force: bool = True) -> str:
    """
    Generate bash command to cleanup a VM completely.
    
    Args:
        vm_name: Name of the VM to cleanup
        force: If True, force destroy even if running
    
    Returns:
        Bash command string for VM cleanup
    """
    return f'''
    VM_NAME="{vm_name}"
    echo "========================================"
    echo "Cleaning up VM: $VM_NAME"
    echo "========================================"
    
    # Try kcli first (if available)
    if command -v kcli &> /dev/null; then
        echo "Attempting kcli cleanup..."
        kcli delete vm "$VM_NAME" -y 2>/dev/null || true
    fi
    
    # Fallback to virsh
    echo "Attempting virsh cleanup..."
    virsh destroy "$VM_NAME" 2>/dev/null || true
    virsh undefine "$VM_NAME" --remove-all-storage 2>/dev/null || true
    virsh undefine "$VM_NAME" 2>/dev/null || true
    
    # Clean up any leftover disk images
    rm -f /var/lib/libvirt/images/$VM_NAME*.qcow2 2>/dev/null || true
    rm -f /var/lib/libvirt/images/$VM_NAME*.img 2>/dev/null || true
    
    echo "VM cleanup complete: $VM_NAME"
    echo "Safe to retrigger DAG"
    '''


def get_cleanup_on_failure_task_command(vm_name_param: str = "{{ params.vm_name }}") -> str:
    """
    Generate bash command for cleanup-on-failure task.
    Uses Jinja template for VM name parameter.
    """
    return f'''
    set +e  # Don't exit on error during cleanup
    
    VM_NAME="{vm_name_param}"
    
    echo "========================================"
    echo "CLEANUP ON FAILURE"
    echo "========================================"
    echo "Cleaning up failed deployment: $VM_NAME"
    echo ""
    
    # Check if VM exists
    if virsh dominfo "$VM_NAME" &>/dev/null; then
        echo "Found VM: $VM_NAME - cleaning up..."
        
        # Stop if running
        virsh destroy "$VM_NAME" 2>/dev/null || true
        sleep 2
        
        # Remove VM and storage
        virsh undefine "$VM_NAME" --remove-all-storage 2>/dev/null || true
        
        echo "VM removed successfully"
    else
        echo "VM not found (may have already been cleaned up)"
    fi
    
    # Also try kcli cleanup
    if command -v kcli &> /dev/null; then
        kcli delete vm "$VM_NAME" -y 2>/dev/null || true
    fi
    
    echo ""
    echo "========================================"
    echo "Cleanup complete - review error above"
    echo "Fix the configuration and retrigger DAG"
    echo "========================================"
    '''


# =============================================================================
# Credential Management Helpers (Bash Commands)
# =============================================================================

def get_credential_setup_command(
    registry_host: str,
    registry_port: str = "8443",
    username_var: str = "quay_username",
    password_var: str = "quay_password",
    pull_secret_path: str = "/root/pull-secret.json",
    output_path: str = "/tmp/merged-pull-secret.json"
) -> str:
    """
    Generate bash command to setup registry credentials.
    Fetches from Airflow Variables and merges with pull-secret.
    """
    registry = f"{registry_host}:{registry_port}"
    
    return f'''
    set -euo pipefail
    
    echo "========================================"
    echo "Setting up registry credentials"
    echo "========================================"
    
    REGISTRY="{registry}"
    PULL_SECRET="{pull_secret_path}"
    OUTPUT="{output_path}"
    
    # Get credentials from Airflow Variables
    echo "Fetching credentials from Airflow Variables..."
    
    # Use airflow CLI to get variables (works inside Airflow container)
    REG_USER=$(airflow variables get {username_var} 2>/dev/null || echo "init")
    REG_PASS=$(airflow variables get {password_var} 2>/dev/null || echo "")
    
    if [ -z "$REG_PASS" ]; then
        echo "ERROR: Password not found in Airflow Variable '{password_var}'"
        echo ""
        echo "To fix, set the variable:"
        echo "  airflow variables set {password_var} '<your-password>'"
        exit 1
    fi
    
    echo "Username: $REG_USER"
    echo "Registry: $REGISTRY"
    
    # Login to registry
    echo ""
    echo "Logging in to registry..."
    podman login "$REGISTRY" -u "$REG_USER" -p "$REG_PASS" --tls-verify=false
    
    # Merge with pull-secret
    if [ -f "$PULL_SECRET" ]; then
        echo ""
        echo "Merging credentials with pull-secret..."
        
        # Create auth string
        AUTH=$(echo -n "$REG_USER:$REG_PASS" | base64 -w0)
        
        # Merge using jq
        jq --arg registry "$REGISTRY" --arg auth "$AUTH" \\
           '.auths[$registry] = {{"auth": $auth}}' \\
           "$PULL_SECRET" > "$OUTPUT"
        
        echo "Merged pull-secret written to: $OUTPUT"
        
        # Verify
        echo ""
        echo "Registries in merged pull-secret:"
        jq -r '.auths | keys[]' "$OUTPUT"
    else
        echo "WARNING: Pull secret not found at $PULL_SECRET"
        echo "Creating minimal auth file..."
        
        AUTH=$(echo -n "$REG_USER:$REG_PASS" | base64 -w0)
        echo '{{"auths": {{"'$REGISTRY'": {{"auth": "'$AUTH'"}}}}}}' > "$OUTPUT"
    fi
    
    echo ""
    echo "Credential setup complete"
    '''


# =============================================================================
# Validation Helpers (Bash Commands)
# =============================================================================

def get_registry_validation_command(
    registry_host: str,
    registry_port: str = "8443",
    min_cert_days: int = 7
) -> str:
    """
    Generate bash command to validate registry health and certificate.
    """
    registry = f"{registry_host}:{registry_port}"
    
    return f'''
    set -euo pipefail
    
    echo "========================================"
    echo "Validating Registry: {registry}"
    echo "========================================"
    
    REGISTRY="{registry}"
    MIN_CERT_DAYS={min_cert_days}
    ERRORS=0
    
    # Check API health
    echo ""
    echo "Checking API health..."
    API_RESPONSE=$(curl -sk "https://$REGISTRY/v2/" 2>&1 || echo "FAILED")
    
    if [ "$API_RESPONSE" == "true" ] || [ "$API_RESPONSE" == "{{}}" ]; then
        echo "  ✅ API responding"
    else
        echo "  ❌ API not responding: $API_RESPONSE"
        ERRORS=$((ERRORS + 1))
    fi
    
    # Check certificate validity
    echo ""
    echo "Checking certificate validity..."
    
    CERT_INFO=$(echo | openssl s_client -connect "$REGISTRY" -servername "{registry_host}" 2>/dev/null | openssl x509 -noout -dates 2>/dev/null || echo "FAILED")
    
    if [ "$CERT_INFO" == "FAILED" ]; then
        echo "  ❌ Could not retrieve certificate"
        ERRORS=$((ERRORS + 1))
    else
        # Extract expiry date
        EXPIRY=$(echo "$CERT_INFO" | grep "notAfter" | cut -d= -f2)
        EXPIRY_EPOCH=$(date -d "$EXPIRY" +%s 2>/dev/null || echo "0")
        NOW_EPOCH=$(date +%s)
        DAYS_LEFT=$(( (EXPIRY_EPOCH - NOW_EPOCH) / 86400 ))
        
        echo "  Certificate expires: $EXPIRY"
        echo "  Days remaining: $DAYS_LEFT"
        
        if [ $DAYS_LEFT -lt $MIN_CERT_DAYS ]; then
            echo "  ❌ Certificate expires in less than $MIN_CERT_DAYS days!"
            echo ""
            echo "  To renew certificate, run:"
            echo "    airflow dags trigger step_ca_operations --conf '{{\\"action\\": \\"renew-cert\\", \\"target\\": \\"{registry_host}\\"}}'"
            ERRORS=$((ERRORS + 1))
        else
            echo "  ✅ Certificate valid for $DAYS_LEFT days"
        fi
    fi
    
    # Summary
    echo ""
    echo "========================================"
    if [ $ERRORS -gt 0 ]; then
        echo "VALIDATION FAILED: $ERRORS error(s)"
        exit 1
    else
        echo "VALIDATION PASSED"
    fi
    '''


def get_dns_validation_command(
    cluster_name: str,
    base_domain: str,
    expected_ip: Optional[str] = None
) -> str:
    """
    Generate bash command to validate DNS entries for OpenShift cluster.
    """
    return f'''
    set -euo pipefail
    
    echo "========================================"
    echo "Validating DNS for: {cluster_name}.{base_domain}"
    echo "========================================"
    
    CLUSTER="{cluster_name}"
    DOMAIN="{base_domain}"
    EXPECTED_IP="{expected_ip or ''}"
    ERRORS=0
    
    # Check api.<cluster>.<domain>
    echo ""
    echo "Checking api.$CLUSTER.$DOMAIN..."
    API_IP=$(dig +short api.$CLUSTER.$DOMAIN 2>/dev/null | head -1)
    
    if [ -z "$API_IP" ]; then
        echo "  ❌ DNS record not found: api.$CLUSTER.$DOMAIN"
        echo ""
        echo "  To fix, run:"
        echo "    airflow dags trigger freeipa_dns_management --conf '{{\\"action\\": \\"add\\", \\"hostname\\": \\"api.$CLUSTER\\", \\"ip\\": \\"<IP>\\"}}'"
        ERRORS=$((ERRORS + 1))
    else
        echo "  ✅ api.$CLUSTER.$DOMAIN -> $API_IP"
        if [ -n "$EXPECTED_IP" ] && [ "$API_IP" != "$EXPECTED_IP" ]; then
            echo "  ⚠️  Warning: Expected $EXPECTED_IP"
        fi
    fi
    
    # Check api-int.<cluster>.<domain>
    echo ""
    echo "Checking api-int.$CLUSTER.$DOMAIN..."
    API_INT_IP=$(dig +short api-int.$CLUSTER.$DOMAIN 2>/dev/null | head -1)
    
    if [ -z "$API_INT_IP" ]; then
        echo "  ❌ DNS record not found: api-int.$CLUSTER.$DOMAIN"
        ERRORS=$((ERRORS + 1))
    else
        echo "  ✅ api-int.$CLUSTER.$DOMAIN -> $API_INT_IP"
    fi
    
    # Check *.apps.<cluster>.<domain> (wildcard)
    echo ""
    echo "Checking *.apps.$CLUSTER.$DOMAIN..."
    APPS_IP=$(dig +short test.apps.$CLUSTER.$DOMAIN 2>/dev/null | head -1)
    
    if [ -z "$APPS_IP" ]; then
        echo "  ❌ Wildcard DNS not found: *.apps.$CLUSTER.$DOMAIN"
        echo ""
        echo "  To fix, add wildcard record in FreeIPA"
        ERRORS=$((ERRORS + 1))
    else
        echo "  ✅ *.apps.$CLUSTER.$DOMAIN -> $APPS_IP"
    fi
    
    # Summary
    echo ""
    echo "========================================"
    if [ $ERRORS -gt 0 ]; then
        echo "DNS VALIDATION FAILED: $ERRORS error(s)"
        echo ""
        echo "Fix DNS records and retrigger this DAG"
        exit 1
    else
        echo "DNS VALIDATION PASSED"
    fi
    '''


def get_config_validation_command(
    cluster_yml_path: str,
    nodes_yml_path: str
) -> str:
    """
    Generate bash command to validate cluster.yml and nodes.yml syntax.
    """
    return f'''
    set -euo pipefail
    
    echo "========================================"
    echo "Validating Configuration Files"
    echo "========================================"
    
    CLUSTER_YML="{cluster_yml_path}"
    NODES_YML="{nodes_yml_path}"
    ERRORS=0
    
    # Check cluster.yml exists
    echo ""
    echo "Checking cluster.yml..."
    if [ ! -f "$CLUSTER_YML" ]; then
        echo "  ❌ File not found: $CLUSTER_YML"
        ERRORS=$((ERRORS + 1))
    else
        echo "  ✅ File exists: $CLUSTER_YML"
        
        # Validate YAML syntax
        if command -v yq &> /dev/null; then
            if yq e '.' "$CLUSTER_YML" > /dev/null 2>&1; then
                echo "  ✅ YAML syntax valid"
            else
                echo "  ❌ YAML syntax error in $CLUSTER_YML"
                echo ""
                yq e '.' "$CLUSTER_YML" 2>&1 | head -5
                ERRORS=$((ERRORS + 1))
            fi
        elif command -v python3 &> /dev/null; then
            if python3 -c "import yaml; yaml.safe_load(open('$CLUSTER_YML'))" 2>/dev/null; then
                echo "  ✅ YAML syntax valid"
            else
                echo "  ❌ YAML syntax error in $CLUSTER_YML"
                ERRORS=$((ERRORS + 1))
            fi
        fi
        
        # Check required fields
        echo ""
        echo "  Checking required fields..."
        for field in cluster_name base_domain; do
            if grep -q "^$field:" "$CLUSTER_YML" 2>/dev/null; then
                VALUE=$(grep "^$field:" "$CLUSTER_YML" | head -1 | cut -d: -f2- | xargs)
                echo "    ✅ $field: $VALUE"
            else
                echo "    ❌ Missing required field: $field"
                ERRORS=$((ERRORS + 1))
            fi
        done
    fi
    
    # Check nodes.yml exists
    echo ""
    echo "Checking nodes.yml..."
    if [ ! -f "$NODES_YML" ]; then
        echo "  ❌ File not found: $NODES_YML"
        ERRORS=$((ERRORS + 1))
    else
        echo "  ✅ File exists: $NODES_YML"
        
        # Validate YAML syntax
        if command -v yq &> /dev/null; then
            if yq e '.' "$NODES_YML" > /dev/null 2>&1; then
                echo "  ✅ YAML syntax valid"
            else
                echo "  ❌ YAML syntax error in $NODES_YML"
                ERRORS=$((ERRORS + 1))
            fi
        fi
        
        # Check for nodes
        NODE_COUNT=$(grep -c "^  - name:" "$NODES_YML" 2>/dev/null || echo "0")
        echo "  Nodes defined: $NODE_COUNT"
        
        if [ "$NODE_COUNT" -eq 0 ]; then
            echo "  ❌ No nodes defined in $NODES_YML"
            ERRORS=$((ERRORS + 1))
        fi
    fi
    
    # Summary
    echo ""
    echo "========================================"
    if [ $ERRORS -gt 0 ]; then
        echo "CONFIG VALIDATION FAILED: $ERRORS error(s)"
        echo ""
        echo "Fix the configuration files and retrigger this DAG"
        exit 1
    else
        echo "CONFIG VALIDATION PASSED"
    fi
    '''


# =============================================================================
# Image Validation Helpers
# =============================================================================

def get_image_validation_command(
    registry_host: str,
    registry_port: str = "8443",
    ocp_version: str = "4.19"
) -> str:
    """
    Generate bash command to validate OCP images exist in registry.
    """
    registry = f"{registry_host}:{registry_port}"
    
    return f'''
    set -euo pipefail
    
    echo "========================================"
    echo "Validating OCP Images in Registry"
    echo "========================================"
    
    REGISTRY="{registry}"
    OCP_VERSION="{ocp_version}"
    ERRORS=0
    
    # Get registry catalog
    echo ""
    echo "Fetching registry catalog..."
    CATALOG=$(curl -sk "https://$REGISTRY/v2/_catalog" 2>/dev/null || echo '{{"repositories":[]}}')
    
    REPO_COUNT=$(echo "$CATALOG" | jq -r '.repositories | length' 2>/dev/null || echo "0")
    echo "Repositories in registry: $REPO_COUNT"
    
    if [ "$REPO_COUNT" -eq 0 ]; then
        echo ""
        echo "❌ Registry is empty - no images found"
        echo ""
        echo "To sync images, run:"
        echo "  airflow dags trigger ocp_registry_sync --conf '{{\\"ocp_version\\": \\"$OCP_VERSION\\"}}'"
        ERRORS=$((ERRORS + 1))
    else
        echo ""
        echo "Checking for OpenShift release images..."
        
        # Check for openshift-release-dev or ocp4 repositories
        if echo "$CATALOG" | jq -r '.repositories[]' | grep -qE "(openshift-release-dev|ocp4|openshift4)"; then
            echo "  ✅ OpenShift release images found"
            
            # List matching repos
            echo ""
            echo "  Matching repositories:"
            echo "$CATALOG" | jq -r '.repositories[]' | grep -E "(openshift-release-dev|ocp4|openshift4)" | head -5 | while read repo; do
                echo "    - $repo"
            done
        else
            echo "  ❌ OpenShift release images not found"
            echo ""
            echo "  Expected repositories like:"
            echo "    - openshift-release-dev/ocp-release"
            echo "    - ocp4/openshift4"
            echo ""
            echo "  To sync images, run:"
            echo "    airflow dags trigger ocp_registry_sync --conf '{{\\"ocp_version\\": \\"$OCP_VERSION\\"}}'"
            ERRORS=$((ERRORS + 1))
        fi
    fi
    
    # Summary
    echo ""
    echo "========================================"
    if [ $ERRORS -gt 0 ]; then
        echo "IMAGE VALIDATION FAILED: $ERRORS error(s)"
        exit 1
    else
        echo "IMAGE VALIDATION PASSED"
    fi
    '''


# =============================================================================
# Airflow Task Generators
# =============================================================================

def create_cleanup_on_failure_task(dag, vm_name_param: str = "{{ params.vm_name }}"):
    """
    Create a BashOperator task for cleanup on failure.
    Import this in your DAG and add to task dependencies.
    
    Usage in DAG:
        from dag_helpers import create_cleanup_on_failure_task
        cleanup = create_cleanup_on_failure_task(dag)
        main_task >> cleanup  # cleanup runs if main_task fails
    """
    from airflow.operators.bash import BashOperator
    from airflow.utils.trigger_rule import TriggerRule
    
    return BashOperator(
        task_id='cleanup_on_failure',
        bash_command=get_cleanup_on_failure_task_command(vm_name_param),
        trigger_rule=TriggerRule.ONE_FAILED,
        dag=dag,
    )

