# Legacy Workflows

These workflows are not actively used and have been moved here to reduce clutter.

GitHub Actions only processes workflows in `.github/workflows/`, so these are effectively disabled.

## Moved Workflows

| Workflow | Description | Reason Moved |
|----------|-------------|--------------|
| `configure-rhel9-equinix.yaml` | Configure RHEL 9 on Equinix Metal | Platform-specific, not general use |
| `configure-rhel9-equinix-vault.yaml` | Same with HashiCorp Vault | Platform-specific, not general use |
| `restart-workflow.yaml` | Auto-restart for RHEL 8 failures | RHEL 8 deprecated, uses old API patterns |

## To Re-enable

If you need to use one of these workflows:

1. Move it back to `.github/workflows/`
2. Update any deprecated actions/syntax
3. Test thoroughly before production use
