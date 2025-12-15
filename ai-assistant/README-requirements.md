# Requirements Management

This project uses `pip-tools` for dependency management to avoid version conflicts and ensure reproducible builds.

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

# Validate no conflicts exist
pip check
```

### Add New Dependency

1. Edit `requirements.in` to add the new package
2. Run `pip-compile requirements.in` to regenerate requirements.txt
3. Run `pip install -r requirements.txt` to install
4. Run `pip check` to validate no conflicts
5. Commit both `requirements.in` and `requirements.txt`

**Example:**
```bash
# Add pydantic-ai to requirements.in
echo "pydantic-ai>=0.2.0" >> requirements.in

# Regenerate locked dependencies
pip-compile requirements.in

# Install and validate
pip install -r requirements.txt
pip check

# Commit both files
git add requirements.in requirements.txt
git commit -m "deps(ai-assistant): Add pydantic-ai for AI orchestration"
```

### Update All Dependencies

```bash
# Update to latest compatible versions
pip-compile --upgrade requirements.in

# Validate the update
pip install -r requirements.txt
pip check
```

### Update Single Package

```bash
# Update just langchain to latest compatible version
pip-compile --upgrade-package langchain requirements.in

# Validate the update
pip install -r requirements.txt
pip check
```

## Why This Approach?

1. **Automatic conflict resolution** - `pip-compile` solves dependency conflicts during compilation
2. **Reproducible builds** - `requirements.txt` locks exact versions for consistent deployments
3. **Easy updates** - One command to upgrade all dependencies safely
4. **Dependabot compatible** - Dependabot can still create PRs for individual package updates
5. **Clear intent** - `requirements.in` shows direct dependencies, not transitive ones
6. **Early conflict detection** - Issues found during development, not in CI

## CI/CD Integration

### Automatic Validation

The CI pipeline automatically validates dependencies in two ways:

1. **On every PR** (`.github/workflows/ai-assistant-ci.yml`):
   - Installs dependencies from `requirements.txt`
   - Runs `pip check` to validate no conflicts exist
   - Fails the build if conflicts are detected

2. **Weekly health check** (`.github/workflows/dependency-health-check.yml`):
   - Runs every Monday at 8am UTC
   - Validates all Python dependency sets across the project
   - Creates GitHub issues if conflicts are found
   - Checks if `requirements.txt` is in sync with `requirements.in`

### Manual Verification

To verify requirements.txt is up-to-date with requirements.in:

```bash
pip install pip-tools
pip-compile requirements.in --output-file=requirements.test.txt --quiet
diff requirements.txt requirements.test.txt
```

Or in CI:

```yaml
- name: Check requirements are up-to-date
  run: |
    cd ai-assistant
    pip install pip-tools
    pip-compile requirements.in --dry-run --quiet
```

## Troubleshooting

### Dependency Conflicts

If `pip check` reports conflicts:

1. **Identify the conflict**: Look for packages with incompatible version requirements
2. **Check requirements.in**: Ensure version constraints aren't too strict
3. **Regenerate**: Run `pip-compile requirements.in` to resolve conflicts
4. **Test**: Run `pip install -r requirements.txt && pip check`

**Example conflict:**
```
grpcio 1.76.0 has requirement protobuf<6.0.0,>=5.0.0, but you have protobuf 6.33.2.
litellm 1.80.10 requires grpcio<1.68.0, but you have grpcio 1.76.0.
```

**Resolution:**
```bash
# Check requirements.in for overly strict constraints
# Remove or relax version pins if appropriate
# Regenerate requirements.txt
pip-compile requirements.in

# Verify the conflict is resolved
pip install -r requirements.txt
pip check
```

### Dependabot PRs

When Dependabot creates a PR to update a package:

1. **Review the PR**: Check what changed and why
2. **Regenerate requirements.txt**: Run `pip-compile requirements.in`
3. **Validate**: Run `pip check` to ensure no conflicts
4. **Test**: Run the test suite to ensure functionality
5. **Merge**: If all checks pass, merge the PR

**Note**: Dependabot updates `requirements.txt` directly. After merging a Dependabot PR, you may need to:
- Update `requirements.in` if version constraints need adjusting
- Run `pip-compile requirements.in` to ensure consistency

### Missing Dependencies

If CI fails with "No module named 'X'":

1. **Add to requirements.in**: The package is missing from requirements.in
2. **Regenerate**: Run `pip-compile requirements.in`
3. **Commit**: Commit both requirements.in and requirements.txt

### Version Conflicts in CI

If CI fails during `pip install`:

1. **Check the error**: Identify which packages conflict
2. **Test locally**: Reproduce the issue locally
3. **Update requirements.in**: Adjust version constraints
4. **Regenerate**: Run `pip-compile requirements.in`
5. **Validate**: Run `pip check` before committing

## Best Practices

1. **Always use pip-compile**: Never manually edit requirements.txt
2. **Validate before committing**: Always run `pip check` after changes
3. **Be specific in requirements.in**: Pin major versions for stability
4. **Test after updates**: Run the full test suite after dependency updates
5. **Review Dependabot PRs**: Don't blindly merge, validate with pip-compile
6. **Keep in sync**: Ensure requirements.txt matches requirements.in

## Related Links

- [pip-tools documentation](https://github.com/jazzband/pip-tools)
- [Dependabot configuration](../.github/dependabot.yml)
- [AI Assistant CI workflow](../.github/workflows/ai-assistant-ci.yml)
- [Dependency health check workflow](../.github/workflows/dependency-health-check.yml)
