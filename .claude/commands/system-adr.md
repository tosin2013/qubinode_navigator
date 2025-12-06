______________________________________________________________________

## description: Search and view Architecture Decision Records allowed-tools: Bash(ls:*), Bash(grep:*), Read, Grep argument-hint: \[topic\]

# Search Architecture Decision Records

You are helping navigate Qubinode Navigator's Architecture Decision Records (ADRs).

Search query: $ARGUMENTS

List all ADRs:
!`ls -la ${QUBINODE_HOME:-$HOME/qubinode_navigator}/docs/adrs/*.md 2>/dev/null | head -30`

Search ADRs for topic:
!`grep -l -i "$ARGUMENTS" ${QUBINODE_HOME:-$HOME/qubinode_navigator}/docs/adrs/*.md 2>/dev/null | head -10`

Key ADRs by topic:

**Architecture**

- ADR-0001: Core architecture decisions
- ADR-0036: Airflow integration

**DAG Development**

- ADR-0045: DAG development standards (critical!)
- ADR-0046: Validation pipeline
- ADR-0047: qubinode-pipelines integration

**Infrastructure**

- ADR-0043: Host network access
- ADR-0050: Hybrid architecture
- ADR-0051: Vault secrets

**AI/RAG**

- ADR-0049: Multi-agent LLM memory
- ADR-0055: Zero-friction services

For the search "$ARGUMENTS", I'll identify:

1. Most relevant ADRs
1. Key decisions and rationale
1. Implementation guidance
1. Related ADRs to review

Read the relevant ADR files to provide detailed information.
