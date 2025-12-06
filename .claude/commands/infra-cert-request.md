______________________________________________________________________

## description: Request a TLS certificate for a hostname allowed-tools: Bash(which:*), Bash(vault:*), Bash(${QUBINODE_HOME:-$HOME/qubinode_navigator}/scripts/qubinode-cert:\*) argument-hint: \[hostname\]

# Request TLS Certificate: $1

You are helping request a TLS certificate in Qubinode Navigator.

Check available certificate authorities:
!`which step-ca >/dev/null 2>&1 && echo "Step-CA available" || echo "Step-CA not found"`
!`vault status 2>/dev/null && echo "Vault available" || echo "Vault not available"`

Request certificate using qubinode-cert:
!`${QUBINODE_HOME:-$HOME/qubinode_navigator}/scripts/qubinode-cert request $1 2>/dev/null || echo "qubinode-cert not found - showing manual steps"`

The qubinode-cert tool auto-selects the best CA (Step-CA > Vault > Let's Encrypt).

After certificate is issued:

1. Verify certificate details
1. Install to appropriate service (nginx, haproxy, etc.)
1. Configure automatic renewal

Manual alternative if script unavailable:

```bash
# Step-CA
step ca certificate $1 $1.crt $1.key

# Vault PKI
vault write pki/issue/qubinode common_name=$1

# Let's Encrypt (certbot)
certbot certonly --standalone -d $1
```
