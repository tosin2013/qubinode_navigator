"""
DAG Helper Functions for ocp4-disconnected-helper
Provides reusable utilities for:
- VM cleanup on failure
- Clear error reporting with file paths
- Credential management via Airflow Variables
- Validation helpers
- User-configurable paths (fixes hardcoded root user issue)

These helpers implement CI/CD-style patterns:
- Idempotent operations
- Self-healing (automatic cleanup)
- Clear error messages pointing to specific files
"""

import os
from datetime import datetime
from typing import Optional, Dict, List, Any

# =============================================================================
# User Configuration Helpers (Fix for hardcoded root user issue)
# =============================================================================


def get_ssh_user() -> str:
    """
    Get SSH user from environment or default to current user.

    Environment variable: QUBINODE_SSH_USER
    Default: Current user from $USER or 'root' if not set

    Returns:
        SSH username to use for connections

    Example:
        >>> user = get_ssh_user()
        >>> ssh_cmd = f"ssh {user}@localhost 'command'"
    """
    return os.environ.get("QUBINODE_SSH_USER", os.environ.get("USER", "root"))


def get_ssh_key_path() -> str:
    """
    Get SSH key path from environment or default to ~/.ssh/id_rsa.

    Environment variable: QUBINODE_SSH_KEY_PATH
    Default: ~/.ssh/id_rsa (expands to current user's home)

    Returns:
        Full path to SSH private key

    Example:
        >>> key_path = get_ssh_key_path()
        >>> ansible_vars = f"ansible_ssh_private_key_file={key_path}"
    """
    default = os.path.expanduser("~/.ssh/id_rsa")
    return os.environ.get("QUBINODE_SSH_KEY_PATH", default)


def get_inventory_dir() -> str:
    """
    Get inventory directory from environment or default to ~/.generated.

    Environment variable: QUBINODE_INVENTORY_DIR
    Default: ~/.generated (expands to current user's home)

    Returns:
        Full path to inventory directory

    Example:
        >>> inv_dir = get_inventory_dir()
        >>> inventory_path = f"{inv_dir}/.{hostname}.{domain}"
    """
    default = os.path.expanduser("~/.generated")
    return os.environ.get("QUBINODE_INVENTORY_DIR", default)


def get_vault_password_file() -> str:
    """
    Get vault password file path from environment or default to ~/.vault_password.

    Environment variable: QUBINODE_VAULT_PASSWORD_FILE
    Default: ~/.vault_password (expands to current user's home)

    Returns:
        Full path to vault password file

    Example:
        >>> vault_file = get_vault_password_file()
        >>> cmd = f"ansible-playbook --vault-password-file {vault_file}"
    """
    default = os.path.expanduser("~/.vault_password")
    return os.environ.get("QUBINODE_VAULT_PASSWORD_FILE", default)


def get_pull_secret_path() -> str:
    """
    Get pull secret path from environment or default to ~/pull-secret.json.

    Environment variable: QUBINODE_PULL_SECRET_PATH
    Default: ~/pull-secret.json (expands to current user's home)

    Returns:
        Full path to pull secret file

    Example:
        >>> pull_secret = get_pull_secret_path()
        >>> cmd = f"cat {pull_secret} | jq '.auths'"
    """
    default = os.path.expanduser("~/pull-secret.json")
    return os.environ.get("QUBINODE_PULL_SECRET_PATH", default)


# =============================================================================
# Error Reporting Helpers
# =============================================================================


def format_config_error(
    config_file: str,
    field: str,
    error_msg: str,
    suggested_fix: Optional[str] = None,
    related_dag: Optional[str] = None,
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
    fix_command: Optional[str] = None,
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


def format_success_report(operation: str, details: Dict[str, Any], next_steps: Optional[List[str]] = None) -> str:
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
    return f"""
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
    """


def get_cleanup_on_failure_task_command(
    vm_name_param: str = "{{ params.vm_name }}",
) -> str:
    """
    Generate bash command for cleanup-on-failure task.
    Uses Jinja template for VM name parameter.
    """
    return f"""
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
    """


# =============================================================================
# Credential Management Helpers (Bash Commands)
# =============================================================================


def get_credential_setup_command(
    registry_host: str,
    registry_port: str = "8443",
    username_var: str = "quay_username",
    password_var: str = "quay_password",
    pull_secret_path: Optional[str] = None,
    output_path: str = "/tmp/merged-pull-secret.json",
) -> str:
    """
    Generate bash command to setup registry credentials.
    Fetches from Airflow Variables and merges with pull-secret.

    Args:
        registry_host: Registry hostname
        registry_port: Registry port (default: "8443")
        username_var: Airflow variable name for username (default: "quay_username")
        password_var: Airflow variable name for password (default: "quay_password")
        pull_secret_path: Path to pull secret (default: None, uses get_pull_secret_path())
        output_path: Output path for merged secret (default: "/tmp/merged-pull-secret.json")
    """
    if pull_secret_path is None:
        pull_secret_path = get_pull_secret_path()

    registry = f"{registry_host}:{registry_port}"

    return f"""
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
    """


# =============================================================================
# Validation Helpers (Bash Commands)
# =============================================================================


def get_registry_validation_command(registry_host: str, registry_port: str = "8443", min_cert_days: int = 7) -> str:
    """
    Generate bash command to validate registry health and certificate.
    """
    registry = f"{registry_host}:{registry_port}"

    return f"""
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
        echo "  [OK] API responding"
    else
        echo "  [ERROR] API not responding: $API_RESPONSE"
        ERRORS=$((ERRORS + 1))
    fi

    # Check certificate validity
    echo ""
    echo "Checking certificate validity..."

    CERT_INFO=$(echo | openssl s_client -connect "$REGISTRY" -servername "{registry_host}" 2>/dev/null | openssl x509 -noout -dates 2>/dev/null || echo "FAILED")

    if [ "$CERT_INFO" == "FAILED" ]; then
        echo "  [ERROR] Could not retrieve certificate"
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
            echo "  [ERROR] Certificate expires in less than $MIN_CERT_DAYS days!"
            echo ""
            echo "  To renew certificate, run:"
            echo "    airflow dags trigger step_ca_operations --conf '{{\\"action\\": \\"renew-cert\\", \\"target\\": \\"{registry_host}\\"}}'"
            ERRORS=$((ERRORS + 1))
        else
            echo "  [OK] Certificate valid for $DAYS_LEFT days"
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
    """


def get_dns_validation_command(cluster_name: str, base_domain: str, expected_ip: Optional[str] = None) -> str:
    """
    Generate bash command to validate DNS entries for OpenShift cluster.
    """
    return f"""
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
        echo "  [ERROR] DNS record not found: api.$CLUSTER.$DOMAIN"
        echo ""
        echo "  To fix, run:"
        echo "    airflow dags trigger freeipa_dns_management --conf '{{\\"action\\": \\"add\\", \\"hostname\\": \\"api.$CLUSTER\\", \\"ip\\": \\"<IP>\\"}}'"
        ERRORS=$((ERRORS + 1))
    else
        echo "  [OK] api.$CLUSTER.$DOMAIN -> $API_IP"
        if [ -n "$EXPECTED_IP" ] && [ "$API_IP" != "$EXPECTED_IP" ]; then
            echo "  [WARN]  Warning: Expected $EXPECTED_IP"
        fi
    fi

    # Check api-int.<cluster>.<domain>
    echo ""
    echo "Checking api-int.$CLUSTER.$DOMAIN..."
    API_INT_IP=$(dig +short api-int.$CLUSTER.$DOMAIN 2>/dev/null | head -1)

    if [ -z "$API_INT_IP" ]; then
        echo "  [ERROR] DNS record not found: api-int.$CLUSTER.$DOMAIN"
        ERRORS=$((ERRORS + 1))
    else
        echo "  [OK] api-int.$CLUSTER.$DOMAIN -> $API_INT_IP"
    fi

    # Check *.apps.<cluster>.<domain> (wildcard)
    echo ""
    echo "Checking *.apps.$CLUSTER.$DOMAIN..."
    APPS_IP=$(dig +short test.apps.$CLUSTER.$DOMAIN 2>/dev/null | head -1)

    if [ -z "$APPS_IP" ]; then
        echo "  [ERROR] Wildcard DNS not found: *.apps.$CLUSTER.$DOMAIN"
        echo ""
        echo "  To fix, add wildcard record in FreeIPA"
        ERRORS=$((ERRORS + 1))
    else
        echo "  [OK] *.apps.$CLUSTER.$DOMAIN -> $APPS_IP"
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
    """


def get_config_validation_command(cluster_yml_path: str, nodes_yml_path: str) -> str:
    """
    Generate bash command to validate cluster.yml and nodes.yml syntax.
    """
    return f"""
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
        echo "  [ERROR] File not found: $CLUSTER_YML"
        ERRORS=$((ERRORS + 1))
    else
        echo "  [OK] File exists: $CLUSTER_YML"

        # Validate YAML syntax
        if command -v yq &> /dev/null; then
            if yq e '.' "$CLUSTER_YML" > /dev/null 2>&1; then
                echo "  [OK] YAML syntax valid"
            else
                echo "  [ERROR] YAML syntax error in $CLUSTER_YML"
                echo ""
                yq e '.' "$CLUSTER_YML" 2>&1 | head -5
                ERRORS=$((ERRORS + 1))
            fi
        elif command -v python3 &> /dev/null; then
            if python3 -c "import yaml; yaml.safe_load(open('$CLUSTER_YML'))" 2>/dev/null; then
                echo "  [OK] YAML syntax valid"
            else
                echo "  [ERROR] YAML syntax error in $CLUSTER_YML"
                ERRORS=$((ERRORS + 1))
            fi
        fi

        # Check required fields
        echo ""
        echo "  Checking required fields..."
        for field in cluster_name base_domain; do
            if grep -q "^$field:" "$CLUSTER_YML" 2>/dev/null; then
                VALUE=$(grep "^$field:" "$CLUSTER_YML" | head -1 | cut -d: -f2- | xargs)
                echo "    [OK] $field: $VALUE"
            else
                echo "    [ERROR] Missing required field: $field"
                ERRORS=$((ERRORS + 1))
            fi
        done
    fi

    # Check nodes.yml exists
    echo ""
    echo "Checking nodes.yml..."
    if [ ! -f "$NODES_YML" ]; then
        echo "  [ERROR] File not found: $NODES_YML"
        ERRORS=$((ERRORS + 1))
    else
        echo "  [OK] File exists: $NODES_YML"

        # Validate YAML syntax
        if command -v yq &> /dev/null; then
            if yq e '.' "$NODES_YML" > /dev/null 2>&1; then
                echo "  [OK] YAML syntax valid"
            else
                echo "  [ERROR] YAML syntax error in $NODES_YML"
                ERRORS=$((ERRORS + 1))
            fi
        fi

        # Check for nodes
        NODE_COUNT=$(grep -c "^  - name:" "$NODES_YML" 2>/dev/null || echo "0")
        echo "  Nodes defined: $NODE_COUNT"

        if [ "$NODE_COUNT" -eq 0 ]; then
            echo "  [ERROR] No nodes defined in $NODES_YML"
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
    """


# =============================================================================
# Image Validation Helpers
# =============================================================================


def get_image_validation_command(registry_host: str, registry_port: str = "8443", ocp_version: str = "4.19") -> str:
    """
    Generate bash command to validate OCP images exist in registry.
    """
    registry = f"{registry_host}:{registry_port}"

    return f"""
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
        echo "[ERROR] Registry is empty - no images found"
        echo ""
        echo "To sync images, run:"
        echo "  airflow dags trigger ocp_registry_sync --conf '{{\\"ocp_version\\": \\"$OCP_VERSION\\"}}'"
        ERRORS=$((ERRORS + 1))
    else
        echo ""
        echo "Checking for OpenShift release images..."

        # Check for openshift-release-dev or ocp4 repositories
        if echo "$CATALOG" | jq -r '.repositories[]' | grep -qE "(openshift-release-dev|ocp4|openshift4)"; then
            echo "  [OK] OpenShift release images found"

            # List matching repos
            echo ""
            echo "  Matching repositories:"
            echo "$CATALOG" | jq -r '.repositories[]' | grep -E "(openshift-release-dev|ocp4|openshift4)" | head -5 | while read repo; do
                echo "    - $repo"
            done
        else
            echo "  [ERROR] OpenShift release images not found"
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
    """


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
        task_id="cleanup_on_failure",
        bash_command=get_cleanup_on_failure_task_command(vm_name_param),
        trigger_rule=TriggerRule.ONE_FAILED,
        dag=dag,
    )


# =============================================================================
# SSH Execution Helpers (ADR-0046 Compliance)
# =============================================================================
# Issue #4 Fix: Provide standardized SSH execution patterns for host commands


def ssh_to_host_command(cmd: str, host: str = "localhost", user: Optional[str] = None) -> str:
    """
    Wrap a command to execute on the host via SSH (ADR-0046).

    Use this for commands that need host access from Airflow containers:
    - kcli commands (VM management)
    - virsh commands (libvirt)
    - ansible-playbook execution
    - Host system commands

    Args:
        cmd: Command to execute on host
        host: Target host (default: localhost)
        user: SSH user (default: None, uses get_ssh_user() for configurable default)

    Returns:
        SSH-wrapped command string using single quotes for clean escaping

    Example:
        >>> ssh_to_host_command("kcli list vm")
        'ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR user@localhost \'kcli list vm\''

    Usage in DAG:
        from dag_helpers import ssh_to_host_command

        bash_command = ssh_to_host_command("kcli list vm")
        # Or with variables (use double quotes in command):
        bash_command = ssh_to_host_command(f'kcli create vm -i centos10stream {vm_name}')
        # Or override user:
        bash_command = ssh_to_host_command("command", user="root")
    """
    if user is None:
        user = get_ssh_user()

    return f"""ssh -o StrictHostKeyChecking=no \\
    -o UserKnownHostsFile=/dev/null \\
    -o LogLevel=ERROR \\
    {user}@{host} \\
    '{cmd}'
    """


def ssh_to_host_script(script: str, host: str = "localhost", user: Optional[str] = None) -> str:
    """
    Execute a multi-line script on the host via SSH (ADR-0046).

    For complex scripts that need host execution. Uses heredoc pattern
    to avoid escaping issues.

    Args:
        script: Multi-line bash script to execute
        host: Target host (default: localhost)
        user: SSH user (default: None, uses get_ssh_user() for configurable default)

    Returns:
        SSH command with heredoc for script execution

    Example:
        script = '''
        kcli list vm
        virsh list --all
        '''
        result = ssh_to_host_script(script)

    Usage in DAG::

        from dag_helpers import ssh_to_host_script

        script = '''
        export VM_NAME="$1"
        kcli info vm "$VM_NAME"
        virsh dominfo "$VM_NAME"
        '''
        bash_command = ssh_to_host_script(script)
        # Or override user:
        bash_command = ssh_to_host_script(script, user="root")
    """
    if user is None:
        user = get_ssh_user()

    return f"""ssh -o StrictHostKeyChecking=no \\
    -o UserKnownHostsFile=/dev/null \\
    -o LogLevel=ERROR \\
    {user}@{host} << 'REMOTE_SCRIPT'
{script}
REMOTE_SCRIPT
    """


def get_kcli_command(cmd: str, via_ssh: bool = True) -> str:
    """
    Generate a kcli command with proper PATH and optional SSH wrapper.

    Args:
        cmd: kcli command (e.g., "list vm", "info vm freeipa")
        via_ssh: Whether to wrap in SSH for host execution (default: True)

    Returns:
        Complete bash command string

    Example:
        >>> get_kcli_command("list vm")
        >>> get_kcli_command("create vm -i centos10stream test-vm")

    Usage in DAG:
        from dag_helpers import get_kcli_command

        list_vms = BashOperator(
            task_id='list_vms',
            bash_command=get_kcli_command("list vm"),
            dag=dag,
        )
    """
    full_cmd = f"""export PATH="/home/airflow/.local/bin:/usr/local/bin:$PATH"
kcli {cmd}"""

    if via_ssh:
        return ssh_to_host_script(full_cmd)
    return full_cmd


def get_ansible_playbook_command(
    playbook_path: str,
    inventory: str = "/opt/qubinode_navigator/inventories/localhost",
    extra_vars: Optional[Dict[str, str]] = None,
    vault_password_file: Optional[str] = None,
    via_ssh: bool = True,
    ssh_user: Optional[str] = None,
) -> str:
    """
    Generate an ansible-playbook command with proper configuration.

    Per ADR-0046, Ansible playbooks should be executed on the host via SSH,
    not inside the Airflow container.

    Args:
        playbook_path: Path to the playbook file
        inventory: Path to inventory directory
        extra_vars: Optional dictionary of extra variables
        vault_password_file: Path to vault password file (default: None, uses get_vault_password_file())
        via_ssh: Whether to wrap in SSH for host execution (default: True)
        ssh_user: SSH user for connection (default: None, uses get_ssh_user())

    Returns:
        Complete bash command string

    Example:
        >>> get_ansible_playbook_command(
        ...     "/opt/freeipa-workshop-deployer/freeipa.yml",
        ...     extra_vars={"action": "create"}
        ... )
    """
    if vault_password_file is None:
        vault_password_file = get_vault_password_file()

    cmd_parts = [
        "ansible-playbook",
        playbook_path,
        f"-i {inventory}",
    ]

    if vault_password_file:
        cmd_parts.append(f"--vault-password-file {vault_password_file}")

    if extra_vars:
        for key, value in extra_vars.items():
            cmd_parts.append(f'-e "{key}={value}"')

    full_cmd = " ".join(cmd_parts)

    if via_ssh:
        return ssh_to_host_script(full_cmd, user=ssh_user)
    return full_cmd
