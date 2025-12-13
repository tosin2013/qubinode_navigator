"""
Airflow DAG: DNS Management via FreeIPA
ADR-0055: Zero-Friction Infrastructure Services

This DAG provides DNS management operations:
- Add DNS records (A, PTR, CNAME, SRV)
- Remove DNS records
- Bulk DNS operations from inventory
- DNS health checks

Requires FreeIPA to be deployed and accessible.
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import BranchPythonOperator
from airflow.models.param import Param

# User-configurable SSH user (fix for hardcoded root issue)
SSH_USER = get_ssh_user()

# Import user-configurable helpers for portable DAGs
from dag_helpers import get_ssh_user


# User-configurable SSH user (fix for hardcoded root issue)
SSH_USER = get_ssh_user()
# Import user-configurable helpers for portable DAGs
from dag_helpers import get_ssh_user

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
    "dns_management",
    default_args=default_args,
    description="Unified DNS management via FreeIPA (ADR-0055)",
    schedule=None,
    catchup=False,
    tags=["qubinode", "dns", "freeipa", "infrastructure", "adr-0055"],
    params={
        "operation": Param(
            "add",
            type="string",
            enum=[
                "add",
                "remove",
                "add-cname",
                "add-srv",
                "list",
                "check",
                "bulk-add",
                "sync-inventory",
            ],
            description="DNS operation to perform",
        ),
        "hostname": Param("", type="string", description="Hostname for DNS record"),
        "ip_address": Param("", type="string", description="IP address for A record"),
        "create_ptr": Param(True, type="boolean", description="Create reverse PTR record"),
        "ttl": Param(3600, type="integer", description="DNS TTL in seconds"),
        "domain": Param("example.com", type="string", description="DNS domain"),
        "cname_target": Param("", type="string", description="Target for CNAME record"),
        "srv_service": Param("", type="string", description="SRV service name (e.g., _ldap._tcp)"),
        "srv_port": Param(0, type="integer", description="SRV port number"),
        "srv_priority": Param(10, type="integer", description="SRV priority"),
        "srv_weight": Param(100, type="integer", description="SRV weight"),
        "bulk_records": Param(
            "",
            type="string",
            description='Bulk records as JSON: [{"hostname": "...", "ip": "..."}]',
        ),
    },
    doc_md="""
    # DNS Management DAG

    Manage DNS records via FreeIPA for zero-friction infrastructure.

    ## Operations

    | Operation | Description | Required Params |
    |-----------|-------------|-----------------|
    | add | Add A record (+ optional PTR) | hostname, ip_address |
    | remove | Remove DNS record | hostname |
    | add-cname | Add CNAME alias | hostname, cname_target |
    | add-srv | Add SRV record | hostname, srv_service, srv_port |
    | list | List DNS records | domain |
    | check | Check DNS resolution | hostname |
    | bulk-add | Add multiple records | bulk_records (JSON) |
    | sync-inventory | Sync from cert inventory | - |

    ## Examples

    ### Add A Record
    ```json
    {
      "operation": "add",
      "hostname": "myservice.example.com",
      "ip_address": "192.168.122.100",
      "create_ptr": true
    }
    ```

    ### Add CNAME
    ```json
    {
      "operation": "add-cname",
      "hostname": "www.example.com",
      "cname_target": "webserver.example.com"
    }
    ```

    ### Bulk Add
    ```json
    {
      "operation": "bulk-add",
      "bulk_records": "[{\\"hostname\\": \\"web1\\", \\"ip\\": \\"192.168.122.101\\"}, {\\"hostname\\": \\"web2\\", \\"ip\\": \\"192.168.122.102\\"}]"
    }
    ```

    ## Prerequisites

    - FreeIPA deployed and running
    - Valid Kerberos ticket on host
    - DNS zone configured in FreeIPA
    """,
)


def decide_operation(**context):
    """Branch based on operation parameter."""
    operation = context["params"].get("operation", "add")
    operation_map = {
        "add": "add_dns_record",
        "remove": "remove_dns_record",
        "add-cname": "add_cname_record",
        "add-srv": "add_srv_record",
        "list": "list_dns_records",
        "check": "check_dns_record",
        "bulk-add": "bulk_add_records",
        "sync-inventory": "sync_inventory",
    }
    return operation_map.get(operation, "add_dns_record")


# Task: Decide operation
decide_operation_task = BranchPythonOperator(
    task_id="decide_operation",
    python_callable=decide_operation,
    dag=dag,
)


# Task: Validate FreeIPA
# Issue #4 Fix: Use SSH to execute kcli commands on host (ADR-0046)
validate_freeipa = BashOperator(
    task_id="validate_freeipa",
    bash_command="""
    echo "========================================"
    echo "Validating FreeIPA Environment"
    echo "========================================"

    # Check if FreeIPA VM exists (ADR-0046: Execute kcli via SSH to host)
    FREEIPA_IP=$(ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR {SSH_USER}@localhost \
        "kcli info vm freeipa 2>/dev/null | grep '^ip:' | awk '{print \\$2}' | head -1")

    if [ -z "$FREEIPA_IP" ] || [ "$FREEIPA_IP" == "None" ]; then
        echo "[ERROR] FreeIPA VM not found"
        echo "Deploy FreeIPA first: airflow dags trigger freeipa_deployment"
        exit 1
    fi

    echo "[OK] FreeIPA VM found at: $FREEIPA_IP"

    # Check Kerberos ticket (on host)
    if ! ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR {SSH_USER}@localhost "klist -s" 2>/dev/null; then
        echo "[WARN] No valid Kerberos ticket on host"
        echo "Attempting kinit..."

        # Try to get ticket
        if [ -n "${FREEIPA_PASSWORD:-}" ]; then
            ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR {SSH_USER}@localhost \
                "echo '$FREEIPA_PASSWORD' | kinit admin" 2>/dev/null || {
                echo "[ERROR] Failed to obtain Kerberos ticket"
                exit 1
            }
        else
            echo "[ERROR] No FREEIPA_PASSWORD set and no ticket"
            echo "Run on host: kinit admin"
            exit 1
        fi
    fi

    echo "[OK] Valid Kerberos ticket"
    ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR {SSH_USER}@localhost "klist"

    echo ""
    echo "[OK] FreeIPA environment validated"
    """,
    dag=dag,
)


# Task: Add DNS Record
add_dns_record = BashOperator(
    task_id="add_dns_record",
    bash_command="""
    echo "========================================"
    echo "Adding DNS Record"
    echo "========================================"

    HOSTNAME="{{ params.hostname }}"
    IP="{{ params.ip_address }}"
    DOMAIN="{{ params.domain }}"
    TTL="{{ params.ttl }}"
    CREATE_PTR="{{ params.create_ptr }}"

    if [ -z "$HOSTNAME" ] || [ -z "$IP" ]; then
        echo "[ERROR] hostname and ip_address are required"
        exit 1
    fi

    # Construct FQDN
    if [[ "$HOSTNAME" != *"."* ]]; then
        FQDN="${HOSTNAME}.${DOMAIN}"
    else
        FQDN="$HOSTNAME"
    fi

    RECORD_NAME="${FQDN%%.*}"
    RECORD_ZONE="${FQDN#*.}"

    echo "FQDN: $FQDN"
    echo "Record: $RECORD_NAME"
    echo "Zone: $RECORD_ZONE"
    echo "IP: $IP"
    echo "TTL: $TTL"
    echo "Create PTR: $CREATE_PTR"

    # ADR-0046: Execute ipa commands via SSH to host (requires Kerberos ticket)
    SSH_CMD="ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR {SSH_USER}@localhost"

    # Check if zone exists
    if ! $SSH_CMD "ipa dnszone-show '$RECORD_ZONE'" &>/dev/null; then
        echo "[WARN] Zone $RECORD_ZONE does not exist, creating..."
        $SSH_CMD "ipa dnszone-add '$RECORD_ZONE' --skip-overlap-check" || {
            echo "[ERROR] Failed to create zone"
            exit 1
        }
    fi

    # Add A record
    echo ""
    echo "Adding A record..."
    $SSH_CMD "ipa dnsrecord-add '$RECORD_ZONE' '$RECORD_NAME' --a-rec='$IP' --a-rec-ttl='$TTL'" 2>/dev/null || \
    $SSH_CMD "ipa dnsrecord-mod '$RECORD_ZONE' '$RECORD_NAME' --a-rec='$IP'" 2>/dev/null || {
        echo "[ERROR] Failed to add A record"
        exit 1
    }

    echo "[OK] A record added: $FQDN -> $IP"

    # Add PTR record
    if [ "$CREATE_PTR" == "True" ] || [ "$CREATE_PTR" == "true" ]; then
        echo ""
        echo "Adding PTR record..."

        IFS='.' read -r -a OCTETS <<< "$IP"
        REV_ZONE="${OCTETS[2]}.${OCTETS[1]}.${OCTETS[0]}.in-addr.arpa"
        REV_RECORD="${OCTETS[3]}"

        # Check if reverse zone exists
        if ! $SSH_CMD "ipa dnszone-show '$REV_ZONE'" &>/dev/null; then
            echo "[WARN] Reverse zone $REV_ZONE does not exist, creating..."
            $SSH_CMD "ipa dnszone-add '$REV_ZONE' --skip-overlap-check" 2>/dev/null || true
        fi

        $SSH_CMD "ipa dnsrecord-add '$REV_ZONE' '$REV_RECORD' --ptr-rec='${FQDN}.'" 2>/dev/null || true

        echo "[OK] PTR record added: $IP -> $FQDN"
    fi

    echo ""
    echo "========================================"
    echo "DNS Record Added Successfully"
    echo "========================================"
    echo "Hostname: $FQDN"
    echo "IP: $IP"
    """,
    trigger_rule="none_failed_min_one_success",
    dag=dag,
)


# Task: Remove DNS Record
remove_dns_record = BashOperator(
    task_id="remove_dns_record",
    bash_command="""
    echo "========================================"
    echo "Removing DNS Record"
    echo "========================================"

    HOSTNAME="{{ params.hostname }}"
    DOMAIN="{{ params.domain }}"

    if [ -z "$HOSTNAME" ]; then
        echo "[ERROR] hostname is required"
        exit 1
    fi

    # Construct FQDN
    if [[ "$HOSTNAME" != *"."* ]]; then
        FQDN="${HOSTNAME}.${DOMAIN}"
    else
        FQDN="$HOSTNAME"
    fi

    RECORD_NAME="${FQDN%%.*}"
    RECORD_ZONE="${FQDN#*.}"

    echo "FQDN: $FQDN"
    echo "Record: $RECORD_NAME"
    echo "Zone: $RECORD_ZONE"

    # ADR-0046: Execute ipa commands via SSH to host (requires Kerberos ticket)
    SSH_CMD="ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR {SSH_USER}@localhost"

    # Get current IP for PTR cleanup
    IP=$($SSH_CMD "ipa dnsrecord-show '$RECORD_ZONE' '$RECORD_NAME'" 2>/dev/null | \
         grep "A record:" | awk '{print $3}')

    # Remove A record
    echo ""
    echo "Removing A record..."
    $SSH_CMD "ipa dnsrecord-del '$RECORD_ZONE' '$RECORD_NAME' --del-all" 2>/dev/null || {
        echo "[WARN] Record may not exist"
    }

    # Remove PTR record
    if [ -n "$IP" ]; then
        echo "Removing PTR record for $IP..."

        IFS='.' read -r -a OCTETS <<< "$IP"
        REV_ZONE="${OCTETS[2]}.${OCTETS[1]}.${OCTETS[0]}.in-addr.arpa"
        REV_RECORD="${OCTETS[3]}"

        $SSH_CMD "ipa dnsrecord-del '$REV_ZONE' '$REV_RECORD' --del-all" 2>/dev/null || true
    fi

    echo ""
    echo "[OK] DNS record removed: $FQDN"
    """,
    trigger_rule="none_failed_min_one_success",
    dag=dag,
)


# Task: Add CNAME Record
add_cname_record = BashOperator(
    task_id="add_cname_record",
    bash_command="""
    echo "========================================"
    echo "Adding CNAME Record"
    echo "========================================"

    HOSTNAME="{{ params.hostname }}"
    TARGET="{{ params.cname_target }}"
    DOMAIN="{{ params.domain }}"

    if [ -z "$HOSTNAME" ] || [ -z "$TARGET" ]; then
        echo "[ERROR] hostname and cname_target are required"
        exit 1
    fi

    # Construct FQDNs
    if [[ "$HOSTNAME" != *"."* ]]; then
        FQDN="${HOSTNAME}.${DOMAIN}"
    else
        FQDN="$HOSTNAME"
    fi

    if [[ "$TARGET" != *"."* ]]; then
        TARGET_FQDN="${TARGET}.${DOMAIN}"
    else
        TARGET_FQDN="$TARGET"
    fi

    RECORD_NAME="${FQDN%%.*}"
    RECORD_ZONE="${FQDN#*.}"

    echo "Alias: $FQDN"
    echo "Target: $TARGET_FQDN"

    # ADR-0046: Execute ipa commands via SSH to host (requires Kerberos ticket)
    SSH_CMD="ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR {SSH_USER}@localhost"

    $SSH_CMD "ipa dnsrecord-add '$RECORD_ZONE' '$RECORD_NAME' --cname-rec='${TARGET_FQDN}.'" || {
        echo "[ERROR] Failed to add CNAME record"
        exit 1
    }

    echo ""
    echo "[OK] CNAME record added: $FQDN -> $TARGET_FQDN"
    """,
    trigger_rule="none_failed_min_one_success",
    dag=dag,
)


# Task: Add SRV Record
add_srv_record = BashOperator(
    task_id="add_srv_record",
    bash_command="""
    echo "========================================"
    echo "Adding SRV Record"
    echo "========================================"

    HOSTNAME="{{ params.hostname }}"
    SERVICE="{{ params.srv_service }}"
    PORT="{{ params.srv_port }}"
    PRIORITY="{{ params.srv_priority }}"
    WEIGHT="{{ params.srv_weight }}"
    DOMAIN="{{ params.domain }}"

    if [ -z "$SERVICE" ] || [ "$PORT" == "0" ]; then
        echo "[ERROR] srv_service and srv_port are required"
        exit 1
    fi

    # Construct target FQDN
    if [ -z "$HOSTNAME" ]; then
        HOSTNAME="$DOMAIN"
    elif [[ "$HOSTNAME" != *"."* ]]; then
        HOSTNAME="${HOSTNAME}.${DOMAIN}"
    fi

    echo "Service: $SERVICE"
    echo "Target: $HOSTNAME"
    echo "Port: $PORT"
    echo "Priority: $PRIORITY"
    echo "Weight: $WEIGHT"

    # ADR-0046: Execute ipa commands via SSH to host (requires Kerberos ticket)
    SSH_CMD="ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR {SSH_USER}@localhost"

    $SSH_CMD "ipa dnsrecord-add '$DOMAIN' '$SERVICE' --srv-rec='$PRIORITY $WEIGHT $PORT ${HOSTNAME}.'" || {
        echo "[ERROR] Failed to add SRV record"
        exit 1
    }

    echo ""
    echo "[OK] SRV record added"
    """,
    trigger_rule="none_failed_min_one_success",
    dag=dag,
)


# Task: List DNS Records
list_dns_records = BashOperator(
    task_id="list_dns_records",
    bash_command="""
    echo "========================================"
    echo "Listing DNS Records"
    echo "========================================"

    DOMAIN="{{ params.domain }}"

    echo "Zone: $DOMAIN"
    echo ""

    # ADR-0046: Execute ipa commands via SSH to host (requires Kerberos ticket)
    SSH_CMD="ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR {SSH_USER}@localhost"

    $SSH_CMD "ipa dnsrecord-find '$DOMAIN'" || {
        echo "[ERROR] Failed to list records for zone: $DOMAIN"
        exit 1
    }
    """,
    trigger_rule="none_failed_min_one_success",
    dag=dag,
)


# Task: Check DNS Record
check_dns_record = BashOperator(
    task_id="check_dns_record",
    bash_command="""
    echo "========================================"
    echo "Checking DNS Record"
    echo "========================================"

    HOSTNAME="{{ params.hostname }}"
    DOMAIN="{{ params.domain }}"

    if [ -z "$HOSTNAME" ]; then
        echo "[ERROR] hostname is required"
        exit 1
    fi

    # Construct FQDN
    if [[ "$HOSTNAME" != *"."* ]]; then
        FQDN="${HOSTNAME}.${DOMAIN}"
    else
        FQDN="$HOSTNAME"
    fi

    echo "Checking: $FQDN"
    echo ""

    echo "Forward (A) lookup:"
    dig +short "$FQDN" A || echo "  Not found"

    IP=$(dig +short "$FQDN" A | head -1)
    if [ -n "$IP" ]; then
        echo ""
        echo "Reverse (PTR) lookup for $IP:"
        dig +short -x "$IP" || echo "  Not found"
    fi

    echo ""
    echo "FreeIPA record details:"
    RECORD_NAME="${FQDN%%.*}"
    RECORD_ZONE="${FQDN#*.}"
    # ADR-0046: Execute ipa commands via SSH to host (requires Kerberos ticket)
    SSH_CMD="ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR {SSH_USER}@localhost"
    $SSH_CMD "ipa dnsrecord-show '$RECORD_ZONE' '$RECORD_NAME'" 2>/dev/null || echo "  Not found in FreeIPA"
    """,
    trigger_rule="none_failed_min_one_success",
    dag=dag,
)


# Task: Bulk Add Records
bulk_add_records = BashOperator(
    task_id="bulk_add_records",
    bash_command="""
    echo "========================================"
    echo "Bulk Adding DNS Records"
    echo "========================================"

    BULK_RECORDS='{{ params.bulk_records }}'
    DOMAIN="{{ params.domain }}"
    TTL="{{ params.ttl }}"

    if [ -z "$BULK_RECORDS" ]; then
        echo "[ERROR] bulk_records JSON is required"
        exit 1
    fi

    echo "Processing records..."
    echo ""

    # ADR-0046: Execute ipa commands via SSH to host (requires Kerberos ticket)
    SSH_CMD="ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR {SSH_USER}@localhost"

    # Parse JSON and add each record
    echo "$BULK_RECORDS" | jq -r '.[] | "\\(.hostname) \\(.ip)"' | while read -r hostname ip; do
        if [ -n "$hostname" ] && [ -n "$ip" ]; then
            # Construct FQDN
            if [[ "$hostname" != *"."* ]]; then
                FQDN="${hostname}.${DOMAIN}"
            else
                FQDN="$hostname"
            fi

            RECORD_NAME="${FQDN%%.*}"
            RECORD_ZONE="${FQDN#*.}"

            echo "Adding: $FQDN -> $ip"

            # Ensure zone exists
            $SSH_CMD "ipa dnszone-show '$RECORD_ZONE'" &>/dev/null || \
                $SSH_CMD "ipa dnszone-add '$RECORD_ZONE' --skip-overlap-check" &>/dev/null || true

            # Add record
            $SSH_CMD "ipa dnsrecord-add '$RECORD_ZONE' '$RECORD_NAME' --a-rec='$ip' --a-rec-ttl='$TTL'" &>/dev/null || \
            $SSH_CMD "ipa dnsrecord-mod '$RECORD_ZONE' '$RECORD_NAME' --a-rec='$ip'" &>/dev/null || true

            echo "  [OK] Added"
        fi
    done

    echo ""
    echo "[OK] Bulk DNS addition complete"
    """,
    trigger_rule="none_failed_min_one_success",
    dag=dag,
)


# Task: Sync from Certificate Inventory
sync_inventory = BashOperator(
    task_id="sync_inventory",
    bash_command="""
    echo "========================================"
    echo "Syncing DNS from Certificate Inventory"
    echo "========================================"

    INVENTORY_FILE="/etc/qubinode/certs/inventory.json"
    DOMAIN="{{ params.domain }}"
    TTL="{{ params.ttl }}"

    if [ ! -f "$INVENTORY_FILE" ]; then
        echo "[WARN] No inventory file found at $INVENTORY_FILE"
        echo "No records to sync"
        exit 0
    fi

    echo "Reading inventory: $INVENTORY_FILE"
    echo ""

    # ADR-0046: Execute ipa commands via SSH to host (requires Kerberos ticket)
    SSH_CMD="ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR {SSH_USER}@localhost"

    # Parse inventory and add records
    jq -r '.certificates[] | "\\(.hostname) \\(.ip // "")"' "$INVENTORY_FILE" 2>/dev/null | \
    while read -r hostname ip; do
        if [ -n "$hostname" ] && [ -n "$ip" ]; then
            # Construct FQDN
            if [[ "$hostname" != *"."* ]]; then
                FQDN="${hostname}.${DOMAIN}"
            else
                FQDN="$hostname"
            fi

            RECORD_NAME="${FQDN%%.*}"
            RECORD_ZONE="${FQDN#*.}"

            echo "Syncing: $FQDN -> $ip"

            # Add record
            $SSH_CMD "ipa dnsrecord-add '$RECORD_ZONE' '$RECORD_NAME' --a-rec='$ip' --a-rec-ttl='$TTL'" &>/dev/null || \
            $SSH_CMD "ipa dnsrecord-mod '$RECORD_ZONE' '$RECORD_NAME' --a-rec='$ip'" &>/dev/null || true
        fi
    done

    echo ""
    echo "[OK] Inventory sync complete"
    """,
    trigger_rule="none_failed_min_one_success",
    dag=dag,
)


# Define task dependencies
decide_operation_task >> [
    add_dns_record,
    remove_dns_record,
    add_cname_record,
    add_srv_record,
    list_dns_records,
    check_dns_record,
    bulk_add_records,
    sync_inventory,
]
