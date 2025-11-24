# MCP Server Tests

This directory contains automated tests for the Qubinode Navigator MCP servers using the `tosin2013.mcp_audit` Ansible collection.

## Overview

Tests validate:
- **AI Assistant MCP Server** (Port 8081) - 3 tools
- **Airflow MCP Server** (Port 8889) - 9 tools

## Quick Start

### 1. Install Test Collection
```bash
make mcp-install
```

### 2. Run Tests

```bash
# Test all MCP servers
make test-mcp

# Test individual servers
make test-mcp-ai        # AI Assistant only
make test-mcp-airflow   # Airflow only

# Generate and view reports
make test-mcp-report
```

### 3. View Results

```bash
# AI Assistant test results
cat tests/mcp/ai_assistant_test_report.md

# Airflow test results
cat tests/mcp/airflow_test_report.md

# Combined results
cat tests/mcp/comprehensive_test_report.md
```

## Test Files

| File | Purpose |
|------|---------|
| `test_ai_assistant_mcp.yml` | Tests AI Assistant MCP server |
| `test_airflow_mcp.yml` | Tests Airflow MCP server |
| `test_mcp_suite.yml` | Comprehensive test suite for both servers |
| `README.md` | This file |

## Running Individual Tests

### AI Assistant Tests
```bash
# All AI tests
ansible-playbook tests/mcp/test_ai_assistant_mcp.yml

# Discovery only
ansible-playbook tests/mcp/test_ai_assistant_mcp.yml --tags discovery

# Specific tool
ansible-playbook tests/mcp/test_ai_assistant_mcp.yml --tags query_documents
```

### Airflow Tests
```bash
# All Airflow tests
ansible-playbook tests/mcp/test_airflow_mcp.yml

# Discovery only
ansible-playbook tests/mcp/test_airflow_mcp.yml --tags discovery

# Specific tests
ansible-playbook tests/mcp/test_airflow_mcp.yml --tags dags
ansible-playbook tests/mcp/test_airflow_mcp.yml --tags vms
```

## Environment Variables

Tests use API keys from environment variables or defaults from your configuration:

```bash
# Optional: Set explicitly
export MCP_API_KEY="your-ai-assistant-api-key"
export AIRFLOW_MCP_API_KEY="your-airflow-api-key"
```

Default keys are loaded from `MCP-CONFIGURATION-ACTIVE.md`.

## Test Tags

Use tags to run specific test categories:

| Tag | Description |
|-----|-------------|
| `discovery` | Server capability discovery |
| `tools` | Tool execution tests |
| `validation` | Response validation |
| `report` | Report generation |
| `dags` | DAG-related tests |
| `vms` | VM-related tests |
| `suite` | Full test suite |

## Expected Test Results

### AI Assistant Tests
- ✅ Server discovery successful
- ✅ 3 tools tested: query_documents, chat_with_context, get_project_status
- ✅ Test report generated

### Airflow Tests
- ✅ Server discovery successful
- ✅ Core tools tested: list_dags, list_vms
- ✅ Optional tool tests (may skip if resources don't exist)
- ✅ Test report generated

## Troubleshooting

### Connection Refused
```bash
# Check MCP servers are running
podman ps | grep airflow

# Check ports are accessible
curl -I http://localhost:8081
curl -I http://localhost:8889
```

### Authentication Errors
```bash
# Verify API keys in .env file
grep MCP_API_KEY /root/qubinode_navigator/airflow/.env
grep AIRFLOW_MCP_API_KEY /root/qubinode_navigator/airflow/.env
```

### Timeout Issues
```bash
# Run with increased verbosity
ansible-playbook tests/mcp/test_mcp_suite.yml -vv

# Check server logs
podman logs -f airflow_airflow-webserver_1 | grep MCP
```

## CI/CD Integration

Tests can be integrated into your CI/CD pipeline. See `MCP-AUDIT-INTEGRATION.md` for examples of:
- GitLab CI integration
- GitHub Actions workflows
- Automated test reporting

## Additional Resources

- **Integration Guide**: `/root/qubinode_navigator/MCP-AUDIT-INTEGRATION.md`
- **MCP Configuration**: `/root/qubinode_navigator/MCP-CONFIGURATION-ACTIVE.md`
- **Collection Docs**: https://deepwiki.com/tosin2013/ansible-collection-mcp-audit

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review MCP server logs
3. Consult `MCP-AUDIT-INTEGRATION.md` for detailed examples
