# Requirements Management

This project uses `pip-tools` for dependency management to avoid version conflicts.

## Files

- **`requirements.in`** - High-level dependencies (what you edit)
- **`requirements.txt`** - Locked dependencies (auto-generated, don't edit manually)

## Workflow

### Update Dependencies

```bash
# Install pip-tools
pip install pip-tools

# Generate locked requirements.txt from requirements.in
pip-compile requirements.in

# Install dependencies
pip install -r requirements.txt
```

### Add New Dependency

1. Edit `requirements.in`
1. Run `pip-compile requirements.in`
1. Commit both files

### Update All Dependencies

```bash
# Update to latest compatible versions
pip-compile --upgrade requirements.in
```

### Update Single Package

```bash
# Update just langchain to latest compatible version
pip-compile --upgrade-package langchain requirements.in
```

## Why This Approach?

1. **Automatic conflict resolution** - `pip-compile` solves dependency conflicts
1. **Reproducible builds** - `requirements.txt` locks exact versions
1. **Easy updates** - One command to upgrade all dependencies
1. **Dependabot compatible** - Can still create PRs for updates
1. **Clear intent** - `requirements.in` shows what you actually need

## CI/CD Integration

GitHub Actions should:

1. Install from `requirements.txt` (locked versions)
1. Optionally verify `requirements.txt` is up-to-date with `requirements.in`

```yaml
- name: Check requirements are up-to-date
  run: |
    pip install pip-tools
    pip-compile requirements.in --dry-run --quiet
```
