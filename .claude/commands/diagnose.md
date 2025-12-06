______________________________________________________________________

## description: AI-powered issue diagnosis allowed-tools: Bash(uname:*), Bash(free:*), Bash(df:*), Bash(systemctl:*), Bash(journalctl:*), Bash(tail:*), Bash(curl:\*), Read argument-hint: \[problem-description\]

# Diagnose Issue

You are helping diagnose an issue in Qubinode Navigator.

Problem description: $ARGUMENTS

First, gather system context:
!`echo "=== System Info ===" && uname -a && free -h && df -h / | tail -1`

!`echo "=== Service Status ===" && systemctl is-active libvirtd airflow-webserver postgresql 2>/dev/null || echo "Some services not found"`

!`echo "=== Recent Errors ===" && journalctl -p err --since "1 hour ago" --no-pager 2>/dev/null | tail -20 || echo "No journal access"`

!`echo "=== Airflow Logs ===" && tail -50 ${QUBINODE_HOME:-$HOME/qubinode_navigator}/airflow/logs/scheduler/latest/*.log 2>/dev/null | grep -i error | tail -10 || echo "No recent Airflow errors"`

Query the knowledge base for similar issues:
!`curl -s -X POST http://localhost:8080/api/query -H "Content-Type: application/json" -d '{"query": "troubleshoot $ARGUMENTS"}' 2>/dev/null | head -30`

Based on the gathered information:

1. Identify the root cause
1. Check relevant ADRs for guidance
1. Provide step-by-step resolution
1. Suggest preventive measures
1. Reference similar past issues if found in RAG
