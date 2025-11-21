# HashiCorp Vault Migration and Dynamic Updates Research
**Generated**: 2025-07-09  
**Context**: Enhanced load-variables.py with HashiCorp Vault integration  
**Focus**: Dynamic vault updates based on HashiCorp migration patterns

## Executive Summary

Based on analysis of HashiCorp's official migration documentation and the existing Qubinode Navigator codebase, this document outlines the implementation of dynamic vault updates and migration patterns for transitioning from HCP Vault Secrets to HCP Vault Dedicated or self-hosted Vault.

## Key Findings from HashiCorp Documentation

### Migration Concepts Mapping
| Vault Secrets Concept | Vault Dedicated Equivalent | Qubinode Implementation |
|----------------------|---------------------------|------------------------|
| HCP org owner | Admin token | Root/sudo access |
| HCP API/CLI | Vault API/CLI | hvac Python client |
| App | Secrets engine (KV v2) | ansiblesafe/{environment} |
| HCP IAM roles | Policies | AnsibleSafe permissions |
| Project | Namespaces | INVENTORY environment |

### Current Qubinode Integration Status
- ✅ **Token-based auth**: Already implemented in CI/CD pipelines
- ✅ **KV v2 pattern**: Using `ansiblesafe/{environment}` paths
- ✅ **Environment isolation**: Per-inventory vault configurations
- ✅ **CLI integration**: vault commands in .gitlab-ci.yml files

## Enhanced load-variables.py Implementation

### New Features Added

#### 1. Template-Based Configuration Generation
```python
class EnhancedConfigGenerator:
    def generate_config_template(self, output_path="/tmp/config.yml", 
                                template_name="default.yml.j2"):
        """Generate /tmp/config.yml from Jinja2 templates"""
        variables = self._gather_all_variables()  # Env + Vault + Interactive
        config_content = self._render_template(template_name, variables)
        return self._write_secure_config(config_content, output_path)
```

#### 2. HashiCorp Vault Integration
```python
def _init_vault_client(self):
    """Initialize HashiCorp Vault client using hvac"""
    vault_addr = os.environ.get('VAULT_ADDR')
    vault_token = os.environ.get('VAULT_TOKEN')
    
    if vault_addr and vault_token:
        self.vault_client = hvac.Client(url=vault_addr, token=vault_token)
```

#### 3. Dynamic Vault Updates
```python
def update_vault_with_config(self, config_path="/tmp/config.yml"):
    """Update HashiCorp Vault with configuration values"""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    secret_path = f"ansiblesafe/{self.inventory_env}"
    self.vault_client.secrets.kv.v2.create_or_update_secret(
        path=secret_path, secret=config
    )
```

### Variable Priority Hierarchy
1. **Environment variables** (highest priority)
2. **HashiCorp Vault** (if enabled and available)
3. **Interactive prompts** (for missing required fields)
4. **Template defaults** (lowest priority)

## Migration Patterns Implementation

### Pattern 1: Gradual Migration
```bash
# Phase 1: Dual operation (current + vault)
export USE_HASHICORP_VAULT="true"
export VAULT_ADDR="https://vault.company.com"
export VAULT_TOKEN="hvs.CAESIJ..."

# Generate config with vault fallback
python3 enhanced-load-variables.py --generate-config --update-vault
```

### Pattern 2: Vault-First Operation
```bash
# Phase 2: Vault-primary with local fallback
export USE_HASHICORP_VAULT="true"
export VAULT_ADDR="https://vault.company.com"

# All secrets from vault, generate local config for ansiblesafe
python3 enhanced-load-variables.py --generate-config --template vault-primary.yml.j2
```

### Pattern 3: Migration Script Integration
Based on HashiCorp's example migration script, adapted for Qubinode:

```python
def migrate_ansiblesafe_to_vault(self):
    """Migrate existing ansiblesafe configurations to HashiCorp Vault"""
    
    # Read existing vault.yml (decrypted)
    vault_path = f"inventories/{self.inventory_env}/group_vars/control/vault.yml"
    
    # Decrypt using ansiblesafe
    subprocess.run(["/usr/local/bin/ansiblesafe", "-f", vault_path, "-o", "2"])
    
    # Read decrypted content
    with open(vault_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Upload to HashiCorp Vault
    secret_path = f"ansiblesafe/{self.inventory_env}"
    self.vault_client.secrets.kv.v2.create_or_update_secret(
        path=secret_path, secret=config
    )
    
    # Re-encrypt local file
    subprocess.run(["/usr/local/bin/ansiblesafe", "-f", vault_path, "-o", "1"])
```

## Template System Architecture

### Template Features
- **Environment-specific logic**: Conditional blocks for different environments
- **Vault integration**: `vault_get()` function for dynamic secret retrieval
- **Fallback handling**: Graceful degradation when vault unavailable
- **Security metadata**: Template generation tracking

### Example Template Usage
```yaml
# templates/default.yml.j2
{% raw %}
{% if vault_enabled %}
offline_token: {{ vault_get('tokens/offline_token') or offline_token | default('') }}
{% else %}
offline_token: {{ offline_token | default('') }}
{% endif %}

{% if environment == "production" %}
# Production-specific settings
{% elif environment == "hetzner" %}
# Hetzner-specific settings
{% endif %}
{% endraw %}
```

## Security Considerations

### Secure File Handling
```python
def _write_secure_config(self, content: str, output_path: str):
    """Write configuration with secure permissions"""
    temp_fd, temp_path = tempfile.mkstemp(suffix='.yml', prefix='config_')
    os.chmod(temp_path, 0o600)  # Owner read/write only
    # ... write and move to final location
```

### Memory Protection
- Temporary files with secure permissions (600)
- Automatic cleanup on errors
- No secrets in shell history (existing pattern)
- Secure passphrase generation for encryption

### Vault Authentication
- Token-based authentication (existing pattern)
- Environment variable configuration
- Graceful fallback when vault unavailable
- Connection validation before operations

## Integration with Existing Workflow

### Backward Compatibility
- Maintains all existing `load-variables.py` functionality
- Same command-line arguments supported
- Existing inventory file updates preserved
- AnsibleSafe integration unchanged

### Enhanced Workflow
```bash
# Traditional workflow (still works)
python3 load-variables.py --username admin --domain example.com

# Enhanced workflow with templates
python3 enhanced-load-variables.py --generate-config --template hetzner.yml.j2

# Vault integration workflow
export USE_HASHICORP_VAULT="true"
python3 enhanced-load-variables.py --generate-config --update-vault
```

## Deployment Scenarios

### Scenario 1: Local Development
- Use templates for consistent configuration
- Interactive prompts for missing values
- Local `/tmp/config.yml` generation
- AnsibleSafe encryption (existing pattern)

### Scenario 2: CI/CD Pipeline
- Environment variables for all secrets
- Template-based generation for consistency
- Optional vault updates for centralization
- Existing CI/CD integration maintained

### Scenario 3: Vault Migration
- Gradual migration from ansiblesafe to vault
- Dual-source configuration (vault + local)
- Migration scripts for bulk transfer
- Rollback capabilities

## Implementation Status

### ✅ Completed
- Enhanced load-variables.py with template support
- HashiCorp Vault client integration
- Template directory with examples
- Secure file handling
- Variable priority hierarchy

### 🔧 Next Steps
1. **Install dependencies**: `pip install jinja2 hvac`
2. **Test template generation**: Create test templates
3. **Vault integration testing**: Test with actual vault instance
4. **Migration script development**: Bulk migration utilities
5. **Documentation updates**: User guides and examples

## Usage Examples

### Generate config from template
```bash
cd /home/vpcuser/qubinode_navigator
python3 enhanced-load-variables.py --generate-config --template default.yml.j2
```

### Generate with vault integration
```bash
export USE_HASHICORP_VAULT="true"
export VAULT_ADDR="https://vault.company.com"
export VAULT_TOKEN="hvs.CAESIJ..."
python3 enhanced-load-variables.py --generate-config --update-vault
```

### Environment-specific generation
```bash
export INVENTORY="hetzner"
python3 enhanced-load-variables.py --generate-config --template hetzner.yml.j2
```

This implementation provides a smooth migration path while maintaining full backward compatibility with the existing Qubinode Navigator workflow.
