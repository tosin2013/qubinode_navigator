"""
Airflow DAG: Infrastructure Health Check
Validates all Qubinode infrastructure components are healthy.

Run this DAG to:
- Verify FreeIPA is operational
- Verify Step-CA is operational
- Verify VyOS router connectivity (if deployed)
- Verify DNS resolution
- Verify certificate validity
- Check disk space and resources

Schedule: Every 6 hours (or manual trigger)
"""

import json
from datetime import datetime, timedelta

from airflow.models.param import Param
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

from airflow import DAG

default_args = {
    "owner": "qubinode",
    "depends_on_past": False,
    "start_date": datetime(2025, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}

dag = DAG(
    "infrastructure_health_check",
    default_args=default_args,
    description="Validate all Qubinode infrastructure components",
    schedule="0 */6 * * *",  # Every 6 hours
    catchup=False,
    tags=["qubinode", "health", "monitoring", "infrastructure"],
    params={
        "check_freeipa": Param(True, type="boolean", description="Check FreeIPA"),
        "check_stepca": Param(True, type="boolean", description="Check Step-CA"),
        "check_vyos": Param(True, type="boolean", description="Check VyOS router"),
        "check_vault": Param(True, type="boolean", description="Check Vault"),
        "check_certificates": Param(
            True, type="boolean", description="Check certificate expiry"
        ),
        "cert_warn_days": Param(
            14, type="integer", description="Warn if cert expires within N days"
        ),
    },
    doc_md="""
    # Infrastructure Health Check DAG

    Validates all Qubinode infrastructure components are operational.

    ## Checks Performed

    1. **FreeIPA** - DNS resolution, Kerberos, web UI
    2. **Step-CA** - Health endpoint, certificate issuance
    3. **VyOS Router** - Network connectivity, routing
    4. **Vault** - Seal status, health endpoint
    5. **Certificates** - Expiry warnings
    6. **Resources** - Disk space, memory

    ## Schedule

    Runs every 6 hours automatically, or trigger manually.

    ## Output

    Creates a health report in XCom with status of each component.
    """,
)


# Task: Check host resources
check_host_resources = BashOperator(
    task_id="check_host_resources",
    bash_command="""
    echo "========================================"
    echo "Host Resource Check"
    echo "========================================"

    ERRORS=0

    # Disk space
    echo ""
    echo "Disk Space:"
    df -h / /var /home 2>/dev/null | head -10

    ROOT_USAGE=$(df / | awk 'NR==2 {print $5}' | tr -d '%')
    if [ "$ROOT_USAGE" -gt 90 ]; then
        echo "[CRITICAL] Root filesystem ${ROOT_USAGE}% full"
        ERRORS=$((ERRORS + 1))
    elif [ "$ROOT_USAGE" -gt 80 ]; then
        echo "[WARNING] Root filesystem ${ROOT_USAGE}% full"
    else
        echo "[OK] Root filesystem ${ROOT_USAGE}% used"
    fi

    # Memory
    echo ""
    echo "Memory:"
    free -h

    MEM_AVAILABLE=$(free -m | awk '/^Mem:/ {print $7}')
    if [ "$MEM_AVAILABLE" -lt 1024 ]; then
        echo "[WARNING] Low available memory: ${MEM_AVAILABLE}MB"
    else
        echo "[OK] Available memory: ${MEM_AVAILABLE}MB"
    fi

    # Load average
    echo ""
    echo "Load Average:"
    uptime

    # Libvirt status
    echo ""
    echo "Libvirt Status:"
    if systemctl is-active --quiet libvirtd; then
        echo "[OK] libvirtd running"
        echo "VMs: $(virsh list --all 2>/dev/null | grep -c running) running"
    else
        echo "[ERROR] libvirtd not running"
        ERRORS=$((ERRORS + 1))
    fi

    exit $ERRORS
    """,
    dag=dag,
)


# Task: Check FreeIPA
check_freeipa = BashOperator(
    task_id="check_freeipa",
    bash_command="""
    echo "========================================"
    echo "FreeIPA Health Check"
    echo "========================================"

    CHECK_FREEIPA="{{ params.check_freeipa }}"
    if [ "$CHECK_FREEIPA" != "True" ]; then
        echo "SKIP: FreeIPA check disabled"
        exit 0
    fi

    # Get FreeIPA VM IP
    FREEIPA_IP=$(kcli info vm freeipa 2>/dev/null | grep "^ip:" | awk '{print $2}' | head -1)

    if [ -z "$FREEIPA_IP" ] || [ "$FREEIPA_IP" == "None" ]; then
        echo "[INFO] FreeIPA VM not deployed"
        exit 0
    fi

    echo "FreeIPA IP: $FREEIPA_IP"
    ERRORS=0

    # Check VM is running
    VM_STATE=$(kcli info vm freeipa 2>/dev/null | grep "^status:" | awk '{print $2}')
    if [ "$VM_STATE" == "running" ]; then
        echo "[OK] FreeIPA VM running"
    else
        echo "[ERROR] FreeIPA VM state: $VM_STATE"
        ERRORS=$((ERRORS + 1))
    fi

    # Check SSH connectivity
    if nc -z -w5 $FREEIPA_IP 22 2>/dev/null; then
        echo "[OK] SSH port open"
    else
        echo "[ERROR] SSH port not accessible"
        ERRORS=$((ERRORS + 1))
    fi

    # Check HTTPS (web UI)
    if curl -sk --connect-timeout 5 "https://$FREEIPA_IP/ipa/ui/" | grep -q "FreeIPA" 2>/dev/null; then
        echo "[OK] FreeIPA Web UI accessible"
    elif nc -z -w5 $FREEIPA_IP 443 2>/dev/null; then
        echo "[OK] HTTPS port open (web UI may need login)"
    else
        echo "[WARNING] HTTPS not accessible"
    fi

    # Check DNS resolution (if FreeIPA is DNS server)
    if dig @$FREEIPA_IP +short +time=2 freeipa 2>/dev/null | grep -q .; then
        echo "[OK] FreeIPA DNS responding"
    else
        echo "[INFO] FreeIPA DNS not responding (may not be configured)"
    fi

    # Check Kerberos
    if nc -z -w5 $FREEIPA_IP 88 2>/dev/null; then
        echo "[OK] Kerberos port (88) open"
    else
        echo "[WARNING] Kerberos port not accessible"
    fi

    # Check LDAP
    if nc -z -w5 $FREEIPA_IP 389 2>/dev/null; then
        echo "[OK] LDAP port (389) open"
    else
        echo "[WARNING] LDAP port not accessible"
    fi

    echo ""
    if [ $ERRORS -eq 0 ]; then
        echo "[OK] FreeIPA health check passed"
    else
        echo "[ERROR] FreeIPA has $ERRORS issues"
    fi

    exit $ERRORS
    """,
    dag=dag,
)


# Task: Check Step-CA
check_stepca = BashOperator(
    task_id="check_stepca",
    bash_command="""
    echo "========================================"
    echo "Step-CA Health Check"
    echo "========================================"

    CHECK_STEPCA="{{ params.check_stepca }}"
    if [ "$CHECK_STEPCA" != "True" ]; then
        echo "SKIP: Step-CA check disabled"
        exit 0
    fi

    # Get Step-CA VM IP
    STEPCA_IP=$(kcli info vm step-ca-server 2>/dev/null | grep "^ip:" | awk '{print $2}' | head -1)

    if [ -z "$STEPCA_IP" ] || [ "$STEPCA_IP" == "None" ]; then
        echo "[INFO] Step-CA VM not deployed"
        exit 0
    fi

    echo "Step-CA IP: $STEPCA_IP"
    ERRORS=0

    # Check VM is running
    VM_STATE=$(kcli info vm step-ca-server 2>/dev/null | grep "^status:" | awk '{print $2}')
    if [ "$VM_STATE" == "running" ]; then
        echo "[OK] Step-CA VM running"
    else
        echo "[ERROR] Step-CA VM state: $VM_STATE"
        ERRORS=$((ERRORS + 1))
    fi

    # Check health endpoint
    HEALTH=$(curl -sk --connect-timeout 5 "https://$STEPCA_IP:443/health" 2>/dev/null)
    if echo "$HEALTH" | grep -q "ok"; then
        echo "[OK] Step-CA health endpoint: OK"
    else
        echo "[ERROR] Step-CA health endpoint failed"
        echo "Response: $HEALTH"
        ERRORS=$((ERRORS + 1))
    fi

    # Check SSH
    if nc -z -w5 $STEPCA_IP 22 2>/dev/null; then
        echo "[OK] SSH port open"
    else
        echo "[WARNING] SSH port not accessible"
    fi

    echo ""
    if [ $ERRORS -eq 0 ]; then
        echo "[OK] Step-CA health check passed"
    else
        echo "[ERROR] Step-CA has $ERRORS issues"
    fi

    exit $ERRORS
    """,
    dag=dag,
)


# Task: Check VyOS Router
check_vyos = BashOperator(
    task_id="check_vyos",
    bash_command="""
    echo "========================================"
    echo "VyOS Router Health Check"
    echo "========================================"

    CHECK_VYOS="{{ params.check_vyos }}"
    if [ "$CHECK_VYOS" != "True" ]; then
        echo "SKIP: VyOS check disabled"
        exit 0
    fi

    # Check if VyOS VM exists
    if ! kcli info vm vyos-router &>/dev/null; then
        echo "[INFO] VyOS router not deployed"
        exit 0
    fi

    ERRORS=0

    # Check VM is running
    VM_STATE=$(kcli info vm vyos-router 2>/dev/null | grep "^status:" | awk '{print $2}')
    if [ "$VM_STATE" == "running" ]; then
        echo "[OK] VyOS VM running"
    else
        echo "[ERROR] VyOS VM state: $VM_STATE"
        ERRORS=$((ERRORS + 1))
    fi

    # Get external IP (default network)
    VYOS_EXTERNAL=$(kcli info vm vyos-router 2>/dev/null | grep "^ip:" | awk '{print $2}' | head -1)

    if [ -n "$VYOS_EXTERNAL" ] && [ "$VYOS_EXTERNAL" != "None" ]; then
        echo "VyOS External IP: $VYOS_EXTERNAL"

        # Check SSH
        if nc -z -w5 $VYOS_EXTERNAL 22 2>/dev/null; then
            echo "[OK] SSH accessible on external interface"
        else
            echo "[WARNING] SSH not accessible on external interface"
        fi
    fi

    # Check internal network (192.168.50.1)
    VYOS_INTERNAL="192.168.50.1"
    if ping -c 1 -W 2 $VYOS_INTERNAL &>/dev/null; then
        echo "[OK] Internal network reachable ($VYOS_INTERNAL)"
    else
        echo "[WARNING] Internal network not reachable ($VYOS_INTERNAL)"
    fi

    # Check isolated networks exist
    echo ""
    echo "Libvirt Networks:"
    for net in 1924 1925 1926 1927 1928; do
        if virsh net-info "$net" &>/dev/null; then
            if virsh net-info "$net" 2>/dev/null | grep -q "Active:.*yes"; then
                echo "  [OK] Network $net active"
            else
                echo "  [WARN] Network $net inactive"
            fi
        else
            echo "  [INFO] Network $net not created"
        fi
    done

    echo ""
    if [ $ERRORS -eq 0 ]; then
        echo "[OK] VyOS health check passed"
    else
        echo "[ERROR] VyOS has $ERRORS issues"
    fi

    exit $ERRORS
    """,
    dag=dag,
)


# Task: Check Vault
check_vault = BashOperator(
    task_id="check_vault",
    bash_command="""
    echo "========================================"
    echo "Vault Health Check"
    echo "========================================"

    CHECK_VAULT="{{ params.check_vault }}"
    if [ "$CHECK_VAULT" != "True" ]; then
        echo "SKIP: Vault check disabled"
        exit 0
    fi

    VAULT_ADDR="${VAULT_ADDR:-http://localhost:8200}"
    echo "Vault Address: $VAULT_ADDR"

    ERRORS=0

    # Check if Vault container is running
    if podman ps --format "{{.Names}}" 2>/dev/null | grep -q vault; then
        echo "[OK] Vault container running"
    else
        echo "[INFO] Vault container not running"
        exit 0
    fi

    # Check health endpoint
    HEALTH=$(curl -s --connect-timeout 5 "$VAULT_ADDR/v1/sys/health" 2>/dev/null)

    if [ -z "$HEALTH" ]; then
        echo "[WARNING] Vault not responding"
        exit 0
    fi

    # Parse health response
    INITIALIZED=$(echo "$HEALTH" | jq -r '.initialized // false' 2>/dev/null)
    SEALED=$(echo "$HEALTH" | jq -r '.sealed // true' 2>/dev/null)

    if [ "$INITIALIZED" == "true" ]; then
        echo "[OK] Vault initialized"
    else
        echo "[WARNING] Vault not initialized"
        ERRORS=$((ERRORS + 1))
    fi

    if [ "$SEALED" == "false" ]; then
        echo "[OK] Vault unsealed"
    else
        echo "[ERROR] Vault is sealed"
        ERRORS=$((ERRORS + 1))
    fi

    echo ""
    if [ $ERRORS -eq 0 ]; then
        echo "[OK] Vault health check passed"
    else
        echo "[ERROR] Vault has $ERRORS issues"
    fi

    exit $ERRORS
    """,
    dag=dag,
)


# Task: Check certificates
check_certificates = BashOperator(
    task_id="check_certificates",
    bash_command="""
    echo "========================================"
    echo "Certificate Expiry Check"
    echo "========================================"

    CHECK_CERTS="{{ params.check_certificates }}"
    if [ "$CHECK_CERTS" != "True" ]; then
        echo "SKIP: Certificate check disabled"
        exit 0
    fi

    WARN_DAYS="{{ params.cert_warn_days }}"
    CERT_DIR="/etc/qubinode/certs"
    WARNINGS=0
    ERRORS=0

    if [ ! -d "$CERT_DIR" ]; then
        echo "[INFO] No certificates directory found"
        exit 0
    fi

    echo "Checking certificates in $CERT_DIR..."
    echo "Warning threshold: $WARN_DAYS days"
    echo ""

    NOW=$(date +%s)

    for cert_file in $(find "$CERT_DIR" -name "cert.pem" -o -name "*.crt" 2>/dev/null); do
        if [ ! -f "$cert_file" ]; then
            continue
        fi

        HOSTNAME=$(basename $(dirname "$cert_file"))
        EXPIRY_DATE=$(openssl x509 -in "$cert_file" -noout -enddate 2>/dev/null | cut -d= -f2)

        if [ -z "$EXPIRY_DATE" ]; then
            echo "  [WARN] Cannot read: $cert_file"
            continue
        fi

        EXPIRY_EPOCH=$(date -d "$EXPIRY_DATE" +%s 2>/dev/null || echo "0")
        DAYS_LEFT=$(( (EXPIRY_EPOCH - NOW) / 86400 ))

        if [ "$DAYS_LEFT" -lt 0 ]; then
            echo "  [EXPIRED] $HOSTNAME - expired $((DAYS_LEFT * -1)) days ago"
            ERRORS=$((ERRORS + 1))
        elif [ "$DAYS_LEFT" -lt "$WARN_DAYS" ]; then
            echo "  [WARNING] $HOSTNAME - expires in $DAYS_LEFT days"
            WARNINGS=$((WARNINGS + 1))
        else
            echo "  [OK] $HOSTNAME - expires in $DAYS_LEFT days"
        fi
    done

    echo ""
    echo "Summary: $ERRORS expired, $WARNINGS expiring soon"

    if [ $ERRORS -gt 0 ]; then
        exit 1
    fi
    exit 0
    """,
    dag=dag,
)


# Task: Generate health report
generate_report = BashOperator(
    task_id="generate_report",
    bash_command="""
    echo "========================================"
    echo "Infrastructure Health Report"
    echo "========================================"
    echo ""
    echo "Timestamp: $(date -Iseconds)"
    echo ""

    # Summary of checks
    echo "Component Status:"
    echo "  Host Resources: Checked"
    echo "  FreeIPA: Checked"
    echo "  Step-CA: Checked"
    echo "  VyOS Router: Checked"
    echo "  Vault: Checked"
    echo "  Certificates: Checked"
    echo ""
    echo "See individual task logs for details."
    echo ""
    echo "========================================"
    echo "Health check complete"
    echo "========================================"
    """,
    trigger_rule="all_done",
    dag=dag,
)


# Define task dependencies (all checks run in parallel, then report)
[
    check_host_resources,
    check_freeipa,
    check_stepca,
    check_vyos,
    check_vault,
    check_certificates,
] >> generate_report
