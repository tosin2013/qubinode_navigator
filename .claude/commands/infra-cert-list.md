______________________________________________________________________

## description: List all managed TLS certificates allowed-tools: Bash(${QUBINODE_HOME:-$HOME/qubinode_navigator}/scripts/qubinode-cert:*), Bash(ls:*), Bash(openssl:\*)

# List TLS Certificates

You are helping list TLS certificates in Qubinode Navigator.

List certificates:
!`${QUBINODE_HOME:-$HOME/qubinode_navigator}/scripts/qubinode-cert list 2>/dev/null || echo "Checking certificate locations manually..."`

Check common certificate locations:
!`ls -la /etc/pki/tls/certs/*.crt 2>/dev/null | head -10 || echo "No certs in /etc/pki/tls/certs/"`
!`ls -la /etc/letsencrypt/live/ 2>/dev/null || echo "No Let's Encrypt certs"`

Check certificate expiration:
!`for cert in /etc/pki/tls/certs/*.crt; do echo "=== $cert ===" && openssl x509 -in "$cert" -noout -dates 2>/dev/null; done | head -30`

For each certificate, report:

1. Hostname/CN
1. Issuer (CA)
1. Expiration date
1. Days until expiry
1. Renewal status

Flag any certificates expiring within 30 days.

$ARGUMENTS
