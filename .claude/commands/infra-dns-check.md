______________________________________________________________________

## description: Check DNS resolution for a hostname allowed-tools: Bash(${QUBINODE_HOME:-$HOME/qubinode_navigator}/scripts/qubinode-dns:*), Bash(dig:*), Bash(nslookup:\*) argument-hint: \[hostname\]

# Check DNS Resolution: $1

You are helping verify DNS resolution in Qubinode Navigator.

Run DNS checks:
!`${QUBINODE_HOME:-$HOME/qubinode_navigator}/scripts/qubinode-dns check $1 2>/dev/null || echo "Running manual checks..."`

Manual DNS verification:
!`echo "=== Forward lookup ===" && dig +short $1 A 2>/dev/null || nslookup $1 2>/dev/null`
!`echo "=== All records ===" && dig $1 ANY +noall +answer 2>/dev/null | head -10`

Check from different nameservers:
!`echo "=== Local resolver ===" && dig @localhost $1 +short 2>/dev/null`
!`echo "=== Google DNS ===" && dig @8.8.8.8 $1 +short 2>/dev/null`

Report:

1. Whether hostname resolves
1. IP address(es) returned
1. Reverse DNS status
1. TTL values
1. Any DNS propagation issues
1. Recommendations if resolution fails
