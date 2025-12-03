# HashiCorp Vault on OpenShift Setup for Qubinode Navigator

### WIP

This guide walks you through deploying HashiCorp Vault on OpenShift and integrating it with the enhanced Qubinode Navigator configuration system.

## Prerequisites

1. **OpenShift Cluster**: Running OpenShift 4.x cluster with admin access
1. **oc CLI**: OpenShift command-line tool installed and configured
1. **Helm** (optional): For Helm-based deployment
1. **Storage**: Persistent storage available for Vault data
1. **Network Access**: Ability to access Vault from Qubinode Navigator

## Deployment Options

### Option A: Vault Operator (Recommended)

### Option B: Helm Chart Deployment

### Option C: Manual YAML Deployment

## Option A: HashiCorp Vault Operator Deployment

### A.1 Install Vault Operator

```bash
# Create namespace for Vault
oc new-project vault-system

# Install Vault Operator from OperatorHub
oc apply -f - << EOF
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: vault-operator
  namespace: vault-system
spec:
  channel: stable
  name: vault
  source: community-operators
  sourceNamespace: openshift-marketplace
EOF

# Wait for operator to be ready
oc get csv -n vault-system
```

### A.2 Deploy Vault Instance

```bash
# Create Vault custom resource
oc apply -f - << EOF
apiVersion: vault.banzaicloud.com/v1alpha1
kind: Vault
metadata:
  name: qubinode-vault
  namespace: vault-system
spec:
  size: 1
  image: hashicorp/vault:1.15.4

  # Storage configuration
  storage:
    - type: "file"
      path: "/vault/data"

  # Service configuration
  serviceType: ClusterIP

  # Ingress configuration
  ingress:
    enabled: true
    spec:
      rules:
      - host: vault.apps.your-cluster.com
        http:
          paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: qubinode-vault
                port:
                  number: 8200

  # Persistent storage
  volumeClaimTemplates:
    - metadata:
        name: vault-data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 10Gi

  # Security context
  securityContext:
    runAsUser: 100
    runAsGroup: 1000
    fsGroup: 1000

  # Configuration
  config:
    storage:
      file:
        path: "/vault/data"
    listener:
      tcp:
        address: "0.0.0.0:8200"
        tls_disable: true
    ui: true
    api_addr: "http://0.0.0.0:8200"
EOF
```

### A.3 Initialize and Unseal Vault

```bash
# Get Vault pod name
VAULT_POD=$(oc get pods -n vault-system -l app=vault -o jsonpath='{.items[0].metadata.name}')

# Initialize Vault
oc exec -n vault-system $VAULT_POD -- vault operator init -key-shares=5 -key-threshold=3

# Save the unseal keys and root token securely!
# Example output:
# Unseal Key 1: <KEY1>
# Unseal Key 2: <KEY2>
# Unseal Key 3: <KEY3>
# Unseal Key 4: <KEY4>
# Unseal Key 5: <KEY5>
# Initial Root Token: <ROOT_TOKEN>

# Unseal Vault (need 3 keys)
oc exec -n vault-system $VAULT_POD -- vault operator unseal <KEY1>
oc exec -n vault-system $VAULT_POD -- vault operator unseal <KEY2>
oc exec -n vault-system $VAULT_POD -- vault operator unseal <KEY3>

# Verify Vault status
oc exec -n vault-system $VAULT_POD -- vault status
```

## Option B: Helm Chart Deployment

### B.1 Install Helm Chart

```bash
# Add HashiCorp Helm repository
helm repo add hashicorp https://helm.releases.hashicorp.com
helm repo update

# Create namespace
oc new-project vault-system

# Create values file for OpenShift
cat > vault-values.yaml << EOF
global:
  openshift: true

server:
  # Image configuration
  image:
    repository: "hashicorp/vault"
    tag: "1.15.4"

  # OpenShift specific configuration
  extraSecretEnvironmentVars:
    - envName: VAULT_CACERT
      secretName: vault-tls
      secretKey: ca.crt

  # Storage configuration
  dataStorage:
    enabled: true
    size: 10Gi
    storageClass: null
    accessMode: ReadWriteOnce

  # Service configuration
  service:
    enabled: true
    type: ClusterIP
    port: 8200

  # Ingress/Route configuration
  ingress:
    enabled: false

  # OpenShift Route
  route:
    enabled: true
    host: vault.apps.your-cluster.com

  # HA configuration (optional)
  ha:
    enabled: false
    replicas: 3

  # Configuration
  config: |
    ui = true

    listener "tcp" {
      tls_disable = 1
      address = "[::]:8200"
      cluster_address = "[::]:8201"
    }

    storage "file" {
      path = "/vault/data"
    }

    # OpenShift specific
    api_addr = "http://0.0.0.0:8200"
    cluster_addr = "http://0.0.0.0:8201"

# UI configuration
ui:
  enabled: true
  serviceType: "ClusterIP"

# Injector (for automatic secret injection)
injector:
  enabled: true
  image:
    repository: "hashicorp/vault-k8s"
    tag: "1.3.1"
EOF

# Deploy Vault
helm install vault hashicorp/vault -n vault-system -f vault-values.yaml

# Wait for deployment
oc get pods -n vault-system -w
```

### B.2 Create OpenShift Route

```bash
# Create route for Vault UI and API
oc create route edge vault-route \
  --service=vault \
  --port=8200 \
  --hostname=vault.apps.your-cluster.com \
  -n vault-system

# Get route URL
VAULT_ADDR=$(oc get route vault-route -n vault-system -o jsonpath='{.spec.host}')
echo "Vault URL: https://$VAULT_ADDR"
```

## Option C: Manual YAML Deployment

### C.1 Create Vault Deployment

```bash
# Create comprehensive Vault deployment
oc apply -f - << EOF
apiVersion: v1
kind: Namespace
metadata:
  name: vault-system
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: vault
  namespace: vault-system
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: vault-config
  namespace: vault-system
data:
  vault.hcl: |
    ui = true

    listener "tcp" {
      address = "0.0.0.0:8200"
      tls_disable = 1
    }

    storage "file" {
      path = "/vault/data"
    }

    api_addr = "http://0.0.0.0:8200"
    cluster_addr = "http://0.0.0.0:8201"
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: vault-data
  namespace: vault-system
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vault
  namespace: vault-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vault
  template:
    metadata:
      labels:
        app: vault
    spec:
      serviceAccountName: vault
      containers:
      - name: vault
        image: hashicorp/vault:1.15.4
        ports:
        - containerPort: 8200
          name: vault-port
        - containerPort: 8201
          name: cluster-port
        env:
        - name: VAULT_ADDR
          value: "http://127.0.0.1:8200"
        - name: VAULT_CONFIG_DIR
          value: "/vault/config"
        - name: VAULT_DATA_DIR
          value: "/vault/data"
        args:
        - "vault"
        - "server"
        - "-config=/vault/config/vault.hcl"
        volumeMounts:
        - name: vault-config
          mountPath: /vault/config
        - name: vault-data
          mountPath: /vault/data
        livenessProbe:
          httpGet:
            path: /v1/sys/health?standbyok=true
            port: 8200
          initialDelaySeconds: 60
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /v1/sys/health?standbyok=true
            port: 8200
          initialDelaySeconds: 10
          periodSeconds: 5
        securityContext:
          capabilities:
            add: ["IPC_LOCK"]
      volumes:
      - name: vault-config
        configMap:
          name: vault-config
      - name: vault-data
        persistentVolumeClaim:
          claimName: vault-data
---
apiVersion: v1
kind: Service
metadata:
  name: vault
  namespace: vault-system
spec:
  selector:
    app: vault
  ports:
  - name: vault-port
    port: 8200
    targetPort: 8200
  - name: cluster-port
    port: 8201
    targetPort: 8201
---
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: vault
  namespace: vault-system
spec:
  host: vault.apps.your-cluster.com
  to:
    kind: Service
    name: vault
  port:
    targetPort: vault-port
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
EOF
```

## Step 2: Configure Vault for Qubinode Navigator

### 2.1 Access Vault and Initialize

```bash
# Get Vault URL
VAULT_ADDR=https://$(oc get route vault -n vault-system -o jsonpath='{.spec.host}')
export VAULT_ADDR

# Initialize Vault (if not done during deployment)
vault operator init -key-shares=5 -key-threshold=3

# Unseal Vault
vault operator unseal <KEY1>
vault operator unseal <KEY2>
vault operator unseal <KEY3>

# Login with root token
vault auth <ROOT_TOKEN>
```

### 2.2 Configure Kubernetes Authentication

```bash
# Enable Kubernetes auth method
vault auth enable kubernetes

# Configure Kubernetes auth
vault write auth/kubernetes/config \
    token_reviewer_jwt="$(oc serviceaccounts get-token vault -n vault-system)" \
    kubernetes_host="https://kubernetes.default.svc:443" \
    kubernetes_ca_cert=@/var/run/secrets/kubernetes.io/serviceaccount/ca.crt

# Create policy for Qubinode Navigator
vault policy write qubinode-navigator - << EOF
# Allow read/write access to ansiblesafe secrets
path "kv/data/ansiblesafe/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "kv/metadata/ansiblesafe/*" {
  capabilities = ["list", "read", "delete"]
}

# Allow token self-renewal
path "auth/token/renew-self" {
  capabilities = ["update"]
}
EOF

# Create Kubernetes role
vault write auth/kubernetes/role/qubinode-navigator \
    bound_service_account_names=qubinode-navigator \
    bound_service_account_namespaces=qubinode-navigator \
    policies=qubinode-navigator \
    ttl=24h
```

### 2.3 Enable and Configure KV Secrets Engine

```bash
# Enable KV v2 secrets engine
vault secrets enable -version=2 kv

# Store Qubinode Navigator secrets
vault kv put kv/ansiblesafe/localhost \
  rhsm_username="your-rhel-username" \
  rhsm_password="your-rhel-password" \
  admin_user_password="your-admin-password"

# Store environment-specific secrets
vault kv put kv/ansiblesafe/hetzner \
  rhsm_username="hetzner-rhel-user" \
  admin_user_password="hetzner-admin-pass"

vault kv put kv/ansiblesafe/equinix \
  rhsm_username="equinix-rhel-user" \
  admin_user_password="equinix-admin-pass"
```

## Step 3: Configure Qubinode Navigator Integration

### 3.1 Update Environment Configuration

```bash
# Add to your .env file
cat >> .env << EOF

# =============================================================================
# OPENSHIFT VAULT CONFIGURATION
# =============================================================================

# Enable OpenShift vault integration
USE_HASHICORP_VAULT=true
USE_HASHICORP_CLOUD=false

# OpenShift vault server configuration
VAULT_ADDR=https://vault.apps.your-cluster.com
VAULT_TOKEN=your-vault-token

# Kubernetes auth (alternative to token)
VAULT_AUTH_METHOD=kubernetes
VAULT_ROLE=qubinode-navigator

# OpenShift specific settings
OPENSHIFT_VAULT=true
VAULT_NAMESPACE=vault-system
EOF
```

### 3.2 Create Service Account for Qubinode Navigator

```bash
# Create namespace for Qubinode Navigator
oc new-project qubinode-navigator

# Create service account
oc create serviceaccount qubinode-navigator -n qubinode-navigator

# Create role binding for vault access
oc create clusterrolebinding qubinode-navigator-vault \
  --clusterrole=system:auth-delegator \
  --serviceaccount=qubinode-navigator:qubinode-navigator
```

### 3.3 Test Integration

```bash
# Test vault connectivity from Qubinode Navigator
export VAULT_ADDR=https://vault.apps.your-cluster.com

# Test with token authentication
vault status

# Test secret retrieval
vault kv get kv/ansiblesafe/localhost

# Test with enhanced script
python3 enhanced-load-variables.py --generate-config --template default.yml.j2
```

## Step 4: Advanced OpenShift Integration

### 4.1 Vault Secrets Operator (VSO)

```bash
# Install Vault Secrets Operator
oc apply -f - << EOF
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: vault-secrets-operator
  namespace: vault-system
spec:
  channel: stable
  name: vault-secrets-operator
  source: community-operators
  sourceNamespace: openshift-marketplace
EOF

# Create VaultConnection
oc apply -f - << EOF
apiVersion: secrets.hashicorp.com/v1beta1
kind: VaultConnection
metadata:
  name: vault-connection
  namespace: qubinode-navigator
spec:
  address: https://vault.apps.your-cluster.com
  skipTLSVerify: true
EOF

# Create VaultAuth
oc apply -f - << EOF
apiVersion: secrets.hashicorp.com/v1beta1
kind: VaultAuth
metadata:
  name: vault-auth
  namespace: qubinode-navigator
spec:
  vaultConnectionRef: vault-connection
  method: kubernetes
  mount: kubernetes
  kubernetes:
    role: qubinode-navigator
    serviceAccount: qubinode-navigator
EOF

# Create VaultStaticSecret
oc apply -f - << EOF
apiVersion: secrets.hashicorp.com/v1beta1
kind: VaultStaticSecret
metadata:
  name: qubinode-secrets
  namespace: qubinode-navigator
spec:
  vaultAuthRef: vault-auth
  mount: kv
  type: kv-v2
  path: ansiblesafe/localhost
  destination:
    name: qubinode-config
    create: true
  refreshAfter: 30s
EOF
```

### 4.2 Pod Integration with Vault Agent

```bash
# Create Vault Agent configuration
oc apply -f - << EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: vault-agent-config
  namespace: qubinode-navigator
data:
  vault-agent.hcl: |
    vault {
      address = "https://vault.apps.your-cluster.com"
    }

    auto_auth {
      method "kubernetes" {
        mount_path = "auth/kubernetes"
        config = {
          role = "qubinode-navigator"
        }
      }

      sink "file" {
        config = {
          path = "/vault/secrets/token"
        }
      }
    }

    template {
      source      = "/vault/templates/config.yml.tpl"
      destination = "/tmp/config.yml"
      perms       = 0600
    }
EOF
```

## Step 5: Monitoring and Maintenance

### 5.1 Vault Health Monitoring

```bash
# Create ServiceMonitor for Prometheus
oc apply -f - << EOF
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: vault-metrics
  namespace: vault-system
spec:
  selector:
    matchLabels:
      app: vault
  endpoints:
  - port: vault-port
    path: /v1/sys/metrics
    params:
      format: ['prometheus']
EOF
```

### 5.2 Backup Configuration

```bash
# Create backup job
oc apply -f - << EOF
apiVersion: batch/v1
kind: CronJob
metadata:
  name: vault-backup
  namespace: vault-system
spec:
  schedule: "0 2 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: vault-backup
            image: hashicorp/vault:1.15.4
            env:
            - name: VAULT_ADDR
              value: "http://vault:8200"
            - name: VAULT_TOKEN
              valueFrom:
                secretKeyRef:
                  name: vault-token
                  key: token
            command:
            - /bin/sh
            - -c
            - |
              vault operator raft snapshot save /backup/vault-$(date +%Y%m%d-%H%M%S).snap
            volumeMounts:
            - name: backup-storage
              mountPath: /backup
          volumes:
          - name: backup-storage
            persistentVolumeClaim:
              claimName: vault-backup-pvc
          restartPolicy: OnFailure
EOF
```

## Troubleshooting

### Common Issues

1. **Pod Security Context**

   ```bash
   # Check security context constraints
   oc get scc
   oc adm policy add-scc-to-user anyuid -z vault -n vault-system
   ```

1. **Storage Issues**

   ```bash
   # Check PVC status
   oc get pvc -n vault-system
   oc describe pvc vault-data -n vault-system
   ```

1. **Network Connectivity**

   ```bash
   # Test internal connectivity
   oc exec -n vault-system deployment/vault -- vault status

   # Test external connectivity
   curl -k https://vault.apps.your-cluster.com/v1/sys/health
   ```

### Debug Commands

```bash
# Check Vault logs
oc logs -f deployment/vault -n vault-system

# Check operator logs (if using operator)
oc logs -f deployment/vault-operator -n vault-system

# Test from inside cluster
oc run vault-test --image=hashicorp/vault:1.15.4 --rm -it -- /bin/sh
```

## Security Considerations

1. **TLS Configuration**: Enable TLS for production deployments
1. **RBAC**: Implement proper role-based access control
1. **Network Policies**: Restrict network access to Vault
1. **Audit Logging**: Enable Vault audit logging
1. **Backup Encryption**: Encrypt backup snapshots
1. **Token Rotation**: Implement regular token rotation

## Next Steps

1. **Deploy Vault** using your preferred method (Operator recommended)
1. **Configure authentication** (Kubernetes auth for OpenShift integration)
1. **Store your secrets** in the KV secrets engine
1. **Test integration** with enhanced-load-variables.py
1. **Set up monitoring** and backup procedures
1. **Implement security hardening** for production use

This setup provides enterprise-grade HashiCorp Vault deployment on OpenShift with full integration for Qubinode Navigator!
