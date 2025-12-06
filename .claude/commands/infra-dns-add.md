______________________________________________________________________

## description: Add a DNS record allowed-tools: Bash(which:*), Bash(ipa:*), Bash(nsupdate:*), Bash(${QUBINODE_HOME:-$HOME/qubinode_navigator}/scripts/qubinode-dns:*), Bash(dig:*), Bash(nslookup:*) argument-hint: \[hostname\] \[ip\]

# Add DNS Record

You are helping add a DNS record in Qubinode Navigator.

Hostname: $1
IP: $2

Check DNS backend availability:
!`which ipa >/dev/null 2>&1 && echo "FreeIPA available" || echo "FreeIPA not found"`
!`which nsupdate >/dev/null 2>&1 && echo "nsupdate available" || echo "nsupdate not found"`

Add DNS record using qubinode-dns:
!`${QUBINODE_HOME:-$HOME/qubinode_navigator}/scripts/qubinode-dns add $1 $2 2>/dev/null || echo "qubinode-dns not found - showing manual steps"`

The qubinode-dns tool:

- Auto-detects FreeIPA or nsupdate backend
- Creates forward (A) record
- Optionally creates reverse (PTR) record

Manual alternatives:

FreeIPA:

```bash
ipa dnsrecord-add <zone> $1 --a-rec=$2
```

nsupdate:

```bash
nsupdate <<EOF
server <dns-server>
update add $1.<zone>. 3600 A $2
send
EOF
```

After adding, verify:
!`dig +short $1 2>/dev/null || nslookup $1 2>/dev/null`
