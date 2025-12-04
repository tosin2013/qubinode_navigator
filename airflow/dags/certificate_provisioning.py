"""
Airflow DAG: Certificate Provisioning
ADR-0054: Unified Certificate Management

This DAG provides certificate management operations using:
- Step-CA (internal PKI)
- Vault PKI (dynamic short-lived certs)
- Let's Encrypt (public-facing services)

Operations:
- request: Request a new certificate
- renew: Renew expiring certificates
- revoke: Revoke a certificate
- list: List all managed certificates
- install-ca: Install CA root to system trust

Usage:
    airflow dags trigger certificate_provisioning --conf '{
        "operation": "request",
        "hostname": "myservice.example.com",
        "ca": "auto",
        "service": "nginx",
        "install": true
    }'
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import BranchPythonOperator
from airflow.utils.trigger_rule import TriggerRule

# Configuration
QUBINODE_CERT_SCRIPT = "/opt/qubinode_navigator/scripts/qubinode-cert"

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
    "certificate_provisioning",
    default_args=default_args,
    description="Unified certificate management (Step-CA, Vault PKI, Let's Encrypt)",
    schedule=None,  # Manual trigger only
    catchup=False,
    tags=[
        "qubinode",
        "security",
        "certificates",
        "step-ca",
        "vault",
        "letsencrypt",
        "adr-0054",
    ],
    params={
        # Operation parameters
        "operation": "request",  # request, renew, revoke, list, install-ca, bulk-request
        # Request parameters
        "hostname": "",
        "ca": "auto",  # auto, step-ca, vault, letsencrypt
        "service": "generic",  # nginx, haproxy, httpd, harbor, postgresql, registry, generic
        "san_list": "",  # comma-separated SANs
        "duration": "",  # e.g., 720h, 30d
        "install": False,  # Auto-install for service
        # Renew parameters
        "renew_all": True,  # Renew all expiring certs
        # Bulk request parameters (JSON list)
        "bulk_hosts": "",  # e.g., '[{"hostname": "a.example.com", "service": "nginx"}, ...]'
        # CA installation
        "ca_to_install": "step-ca",  # step-ca or vault
    },
    doc_md="""
    # Certificate Provisioning DAG

    Unified certificate management supporting three CAs:
    - **Step-CA**: Internal PKI for disconnected/private environments
    - **Vault PKI**: Dynamic short-lived certificates
    - **Let's Encrypt**: Public-facing services with trusted certificates

    ## Operations

    ### Request Certificate
    ```json
    {
        "operation": "request",
        "hostname": "myservice.example.com",
        "ca": "auto",
        "service": "nginx",
        "san_list": "myservice,localhost",
        "duration": "720h",
        "install": true
    }
    ```

    ### Renew Certificates
    ```json
    {
        "operation": "renew",
        "renew_all": true
    }
    ```

    Or renew specific:
    ```json
    {
        "operation": "renew",
        "hostname": "myservice.example.com",
        "renew_all": false
    }
    ```

    ### Revoke Certificate
    ```json
    {
        "operation": "revoke",
        "hostname": "myservice.example.com"
    }
    ```

    ### List Certificates
    ```json
    {
        "operation": "list"
    }
    ```

    ### Bulk Request
    ```json
    {
        "operation": "bulk-request",
        "ca": "step-ca",
        "bulk_hosts": "[{\\"hostname\\": \\"web1.example.com\\", \\"service\\": \\"nginx\\"}, {\\"hostname\\": \\"web2.example.com\\", \\"service\\": \\"nginx\\"}]"
    }
    ```

    ### Install CA Root
    ```json
    {
        "operation": "install-ca",
        "ca_to_install": "step-ca"
    }
    ```

    ## CA Selection

    When `ca=auto`, the system selects based on:
    1. **Public hostname** → Let's Encrypt
    2. **Internal + Step-CA available** → Step-CA
    3. **Vault PKI configured** → Vault

    ## Services

    Supported services with auto-installation:
    - `nginx` - Installs to /etc/nginx/ssl/
    - `haproxy` - Creates combined PEM at /etc/haproxy/certs/
    - `httpd` - Installs to /etc/pki/tls/
    - `harbor` - Installs to /data/cert/
    - `postgresql` - Installs to PGDATA
    - `registry` - Installs to Docker certs.d
    - `generic` - Stores in /etc/qubinode/certs/<hostname>/
    """,
)


def decide_operation(**context):
    """Branch based on operation parameter"""
    operation = context["params"].get("operation", "request")
    valid_operations = [
        "request",
        "renew",
        "revoke",
        "list",
        "install-ca",
        "bulk-request",
    ]
    if operation in valid_operations:
        return operation.replace("-", "_")  # Convert to valid task_id
    return "list"


# Task: Decide operation
decide_operation_task = BranchPythonOperator(
    task_id="decide_operation",
    python_callable=decide_operation,
    dag=dag,
)

# Task: Ensure qubinode-cert is available
ensure_script = BashOperator(
    task_id="ensure_script",
    bash_command=f"""
    echo "========================================"
    echo "Checking qubinode-cert availability"
    echo "========================================"

    if [[ -x "{QUBINODE_CERT_SCRIPT}" ]]; then
        echo "[OK] qubinode-cert found"
        {QUBINODE_CERT_SCRIPT} version
    else
        echo "[INFO] Installing qubinode-cert to host..."
        ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR root@localhost \
            "cp /opt/qubinode_navigator/scripts/qubinode-cert /usr/local/bin/ && \
             chmod +x /usr/local/bin/qubinode-cert"
        echo "[OK] qubinode-cert installed"
    fi
    """,
    dag=dag,
)

# Task: Request certificate
request = BashOperator(
    task_id="request",
    bash_command="""
    export PATH="/home/airflow/.local/bin:/usr/local/bin:$PATH"
    echo "========================================"
    echo "Requesting Certificate"
    echo "========================================"

    HOSTNAME="{{ params.hostname }}"
    CA="{{ params.ca }}"
    SERVICE="{{ params.service }}"
    SAN_LIST="{{ params.san_list }}"
    DURATION="{{ params.duration }}"
    INSTALL="{{ params.install }}"

    if [[ -z "$HOSTNAME" ]]; then
        echo "[ERROR] hostname parameter is required"
        exit 1
    fi

    echo "Hostname: $HOSTNAME"
    echo "CA:       $CA"
    echo "Service:  $SERVICE"

    # Build command
    CMD="qubinode-cert request $HOSTNAME --ca $CA --service $SERVICE"

    if [[ -n "$SAN_LIST" ]]; then
        CMD="$CMD --san '$SAN_LIST'"
    fi

    if [[ -n "$DURATION" ]]; then
        CMD="$CMD --duration $DURATION"
    fi

    if [[ "$INSTALL" == "True" ]] || [[ "$INSTALL" == "true" ]]; then
        CMD="$CMD --install"
    fi

    echo ""
    echo "Running: $CMD"
    echo ""

    # Execute on host
    ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR root@localhost "$CMD"
    """,
    execution_timeout=timedelta(minutes=10),
    dag=dag,
)

# Task: Renew certificates
renew = BashOperator(
    task_id="renew",
    bash_command="""
    export PATH="/home/airflow/.local/bin:/usr/local/bin:$PATH"
    echo "========================================"
    echo "Renewing Certificates"
    echo "========================================"

    HOSTNAME="{{ params.hostname }}"
    RENEW_ALL="{{ params.renew_all }}"

    if [[ "$RENEW_ALL" == "True" ]] || [[ "$RENEW_ALL" == "true" ]]; then
        echo "Renewing all expiring certificates..."
        ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR root@localhost \
            "qubinode-cert renew --all"
    elif [[ -n "$HOSTNAME" ]]; then
        echo "Renewing certificate for: $HOSTNAME"
        ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR root@localhost \
            "qubinode-cert renew $HOSTNAME"
    else
        echo "[ERROR] Either set renew_all=true or provide hostname"
        exit 1
    fi
    """,
    execution_timeout=timedelta(minutes=15),
    dag=dag,
)

# Task: Revoke certificate
revoke = BashOperator(
    task_id="revoke",
    bash_command="""
    export PATH="/home/airflow/.local/bin:/usr/local/bin:$PATH"
    echo "========================================"
    echo "Revoking Certificate"
    echo "========================================"

    HOSTNAME="{{ params.hostname }}"

    if [[ -z "$HOSTNAME" ]]; then
        echo "[ERROR] hostname parameter is required"
        exit 1
    fi

    echo "Revoking certificate for: $HOSTNAME"

    # Auto-confirm revocation in DAG context
    ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR root@localhost \
        "echo 'yes' | qubinode-cert revoke $HOSTNAME"
    """,
    execution_timeout=timedelta(minutes=5),
    dag=dag,
)

# Task: List certificates
list = BashOperator(
    task_id="list",
    bash_command="""
    export PATH="/home/airflow/.local/bin:/usr/local/bin:$PATH"
    echo "========================================"
    echo "Certificate Inventory"
    echo "========================================"

    ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR root@localhost \
        "qubinode-cert list"
    """,
    dag=dag,
)

# Task: Install CA root
install_ca = BashOperator(
    task_id="install_ca",
    bash_command="""
    export PATH="/home/airflow/.local/bin:/usr/local/bin:$PATH"
    echo "========================================"
    echo "Installing CA Root Certificate"
    echo "========================================"

    CA="{{ params.ca_to_install }}"

    echo "Installing $CA root certificate to system trust..."

    ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR root@localhost \
        "qubinode-cert install-ca $CA"
    """,
    execution_timeout=timedelta(minutes=5),
    dag=dag,
)

# Task: Bulk request
bulk_request = BashOperator(
    task_id="bulk_request",
    bash_command="""
    export PATH="/home/airflow/.local/bin:/usr/local/bin:$PATH"
    echo "========================================"
    echo "Bulk Certificate Request"
    echo "========================================"

    CA="{{ params.ca }}"
    BULK_HOSTS='{{ params.bulk_hosts }}'

    if [[ -z "$BULK_HOSTS" ]]; then
        echo "[ERROR] bulk_hosts parameter is required (JSON array)"
        echo 'Example: [{"hostname": "a.example.com", "service": "nginx"}]'
        exit 1
    fi

    echo "Parsing bulk request..."
    echo "$BULK_HOSTS" | jq -c '.[]' | while read -r entry; do
        HOSTNAME=$(echo "$entry" | jq -r '.hostname')
        SERVICE=$(echo "$entry" | jq -r '.service // "generic"')
        SAN=$(echo "$entry" | jq -r '.san // ""')

        echo ""
        echo "========================================"
        echo "Requesting certificate for: $HOSTNAME"
        echo "========================================"

        CMD="qubinode-cert request $HOSTNAME --ca $CA --service $SERVICE"
        if [[ -n "$SAN" ]]; then
            CMD="$CMD --san '$SAN'"
        fi

        ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR root@localhost "$CMD" || \
            echo "[WARN] Failed to request cert for $HOSTNAME"
    done

    echo ""
    echo "========================================"
    echo "Bulk request complete"
    echo "========================================"
    """,
    execution_timeout=timedelta(minutes=30),
    dag=dag,
)

# Task: Summary
summary = BashOperator(
    task_id="summary",
    bash_command="""
    echo ""
    echo "========================================"
    echo "Certificate Operation Complete"
    echo "========================================"
    echo ""
    echo "Operation: {{ params.operation }}"
    echo "Timestamp: $(date -Iseconds)"
    echo ""

    # Show current inventory
    ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR root@localhost \
        "qubinode-cert list" 2>/dev/null || echo "(inventory not available)"
    """,
    trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
    dag=dag,
)

# Define task dependencies
(ensure_script >> decide_operation_task >> [request, renew, revoke, list, install_ca, bulk_request])
request >> summary
renew >> summary
revoke >> summary
list >> summary
install_ca >> summary
bulk_request >> summary
