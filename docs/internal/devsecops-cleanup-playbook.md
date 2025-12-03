# Qubinode Navigator DevSecOps Cleanup Playbook

> **Purpose**: Provide a context-aware, interactive security and documentation cleanup workflow tailored to AI-assisted repositories. Emphasizes analysis-first mindset, human-in-the-loop decision points, and preservation of project architecture.

## 1. Prerequisites & Initial Setup

### 1.1 Tooling Checklist

```bash
# Run once per workstation
./scripts/setup-security-tools.sh
```

Installs Gitleaks, BFG Repo-Cleaner, `pre-commit`, and prepares `.security-backups/` for bundles, file snapshots, and scan artifacts.

### 1.2 Repository Backup Procedure

| Step         | Command                                                                    | Notes                     |
| ------------ | -------------------------------------------------------------------------- | ------------------------- |
| Git bundle   | `git bundle create .security-backups/git-bundles/pre-cleanup.bundle --all` | Captures refs pre-cleanup |
| Working tree | `tar -czf .security-backups/file-backups/$(date +%Y%m%d)-workspace.tgz .`  | Includes untracked files  |
| CI evidence  | `cp -r artifacts/ .security-backups/scan-results/$(date +%Y%m%d)`          | Helpful for audits        |

> ⚠️ **Warning**: Confirm bundles restore successfully before destructive steps (`git clone repo.bundle repo-restore`).

### 1.3 Team Coordination Checklist

- [ ] Announce cleanup window and freeze non-essential pushes
- [ ] Share backup locations and verify restore plan
- [ ] Assign reviewers for interactive findings
- [ ] Document responsibilities for secrets vs. documentation fixes

______________________________________________________________________

## 2. Repository Context Analysis Phase

### 2.1 Repository Knowledge Graph

1. **Structure tree** – captures files → classes → functions.
   ```bash
   python3 scripts/analyze_repo_structure.py > .security-backups/scan-results/structure.json
   ```
1. **Dependency map** – module import graph.
   ```bash
   ./scripts/dependency_graph.sh > .security-backups/scan-results/dependencies.json
   ```
1. **Visualization tips**
   ```bash
   jq '.python_graph | keys' structure.json
   jq '.["core/ai_update_manager.py"]' dependencies.json
   ```

ASCII example:

```
qubinode_navigator/
├── core/            # orchestration + analytics
├── plugins/         # cloud/os/service adapters
├── ai-assistant/    # FastAPI service + configs
├── scripts/         # setup + tooling helpers
└── docs/            # ADRs, context, internal notes
```

### 2.2 Understanding Project Goals

Use `scripts/generate_repo_summary.py` to ingest README + ADR index and produce:

- Functional modules & responsibilities
- Key dependencies (Ansible, FastAPI, cloud SDKs)
- Architecture patterns (container-first execution, Bash + Python orchestration, modular plugins)

> ℹ️ **Info**: Align cleanup actions with ADR themes documented in `docs/adrs/`. Removing architectural context from public docs must be offset by enhancing contributor docs.

______________________________________________________________________

## 3. Interactive Detection Phase

### 3.1 Gitleaks Scanning & Review

```bash
gitleaks detect -c .gitleaks.toml -r .security-backups/scan-results/gitleaks-report.json
python3 scripts/review_gitleaks.py   # interactive classification
```

`.gitleaks.toml` already covers secrets plus AI developer notes (`ai-todo-comments`, `ai-implementation-notes`, `internal-architecture-details`).

### 3.2 Classification Matrix

| Category               | Examples                             | Action                                              | Notes                             |
| ---------------------- | ------------------------------------ | --------------------------------------------------- | --------------------------------- |
| Critical secrets       | API tokens, passwords                | Remove + rotate; trigger BFG if committed           | Never move to docs                |
| Sensitive architecture | Internal topology, private endpoints | Move to `docs/internal/` or sanitize                | Tie back to ADR references        |
| Developer notes        | TODO, Claude notes, debug traces     | Remove if obsolete; otherwise move to `.dev-notes/` | Include owner + expiry metadata   |
| Public documentation   | User guides, READMEs                 | Sanitize phrasing, keep alignment                   | Preserve references for end users |

Interactive CLI decisions stored in `.security-backups/scan-results/gitleaks-review.json` for reproducibility.

______________________________________________________________________

## 4. Impact Analysis Phase

### 4.1 Dependency & Reference Tracing

```bash
# Trace string or symbol usage
python3 scripts/trace_reference.py "AI Assistant container"

# Optional: generate call graph
pyan3 core/*.py --dot > .security-backups/scan-results/core-callgraph.dot
```

Determine whether flagged notes influence public APIs, scripts, or tests before editing.

### 4.2 Risk Scoring

```yaml
severity_weights:
  critical_secret: 5
  sensitive_architecture: 3
  developer_note: 1
impact_modifiers:
  public_api_reference: 3
  referenced_in_tests: 2
  mentioned_in_docs: 1
```

Score findings to prioritize remediation (High ≥6, Medium 3–5, Low \<3).

______________________________________________________________________

## 5. Interactive Cleanup Execution

### 5.1 Current Branch Workflow

```bash
git checkout -b cleanup/devsecops-$(date +%Y%m%d)
python3 scripts/interactive_cleanup.py   # shows diff per action
```

Actions:

1. **Remove** (critical secrets) – replace with env vars, update docs.
1. **Move** (useful notes) – relocate to `.dev-notes/<module>/` or `docs/internal/<topic>/`.
1. **Sanitize** – trim sensitive portions, add ADR references.

Add `.dev-notes/` to `.gitignore` if meant for contributors only.

### 5.2 Verification Steps

| Step                  | Command                                         | Purpose                            |
| --------------------- | ----------------------------------------------- | ---------------------------------- |
| Security regression   | `gitleaks detect -c .gitleaks.toml --no-banner` | Ensure no findings remain          |
| Automated tests       | `pytest tests/unit` or targeted suites          | Catch note-related fixture changes |
| Linting               | `ansible-lint` / `pre-commit run --all-files`   | Validate formatting and hooks      |
| Docs build (optional) | `mkdocs build` or `jekyll build`                | Confirm docs references            |

Rollback options: `git checkout -- <file>`, restore from backups, or reset branch before merge.

______________________________________________________________________

## 6. Git History Cleanup (BFG)

> ⚠️ **Warning**: Coordinate with maintainers; history rewrite requires force push.

1. **Mirror clone**: `git clone --mirror origin repo.git-mirror`.
1. **Run BFG**:
   ```bash
   bfg --delete-files id_rsa --delete-files '*.pem' --replace-text ../bfg-replacements.txt
   git reflog expire --expire=now --all && git gc --prune=now --aggressive
   ```
1. **Verify**: `gitleaks detect`, `git fsck`.
1. **Force push** after team approval; communicate reset instructions for contributors (`git fetch --all`, `git reset --hard origin/main`).

Maintain backup branch (`backup/pre-bfg-YYYYMMDD`) until cleanup validated.

______________________________________________________________________

## 7. Documentation Restructuring

### 7.1 Dual-Audience Strategy

- **`README.md` (Users)**: overview, quick start, deployment options, troubleshooting.
- **`CONTRIBUTING.md` / `docs/internal/` (Contributors)**: architecture decisions, DevSecOps procedures, note locations.
- **`.dev-notes/`**: ephemeral or sensitive developer context (optional, gitignored).

### 7.2 Organizing Moved Content

1. Prefix internal files with metadata block:
   ```yaml
   ---
   audience: contributors
   module: ai-assistant
   origin: scripts/setup-security-tools.sh
   ---
   ```
1. Maintain `docs/internal/index.md` mapping original paths → new locations.
1. Reference ADR IDs when removing context from public docs (e.g., “See ADR-0028 for plugin framework internals”).

______________________________________________________________________

## 8. Prevention & Automation

### 8.1 Pre-commit Hooks

`.pre-commit-config.yaml` snippet:

```yaml
repos:
  - repo: https://github.com/zricethezav/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks
        args: ["protect", "-q", "-c", ".gitleaks.toml"]
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: check-merge-conflict
      - id: end-of-file-fixer
```

Install via `pre-commit install` and enforce in CI.

### 8.2 CI/CD Integration

Add job to `.github/workflows/ai-assistant-ci.yml`:

```yaml
- name: Security scan
  uses: gitleaks/gitleaks-action@v2
  with:
    config-path: .gitleaks.toml
```

Optional: upload `structure.json`, `dependencies.json`, and Gitleaks reports as artifacts for review.

### 8.3 Team Guidelines

- Annotate developer notes as `NOTE(devsecops,owner,expiry): ...`.
- Reference ADRs when documenting architecture in code.
- Conduct quarterly cleanup drills & tabletop exercises for secret exposure scenarios.

______________________________________________________________________

## 9. Ongoing Maintenance

| Frequency     | Task                                                                           |
| ------------- | ------------------------------------------------------------------------------ |
| Monthly       | Run Gitleaks + review `.dev-notes/` growth                                     |
| Quarterly     | Refresh knowledge graph, dependency reports, and documentation mapping         |
| Release cycle | Verify README vs. contributor docs alignment                                   |
| Annually      | Update tooling versions, revisit classification matrix, audit pre-commit hooks |

**Monitoring Ideas**

- Dashboards tracking number of developer notes relocated vs. removed
- Heat map of directories with repeated findings
- ADR coverage report (files lacking references)

**Continuous Improvement**

1. Capture lessons learned inside `docs/internal/devsecops-playbook.md` (this file).
1. Extend `.gitleaks.toml` as new AI note patterns emerge.
1. Automate reporting (e.g., Slack notifications on new critical findings).

______________________________________________________________________

### Troubleshooting Quick Reference

- **False positives**: add targeted allowlists or annotate sample values (`PLACEHOLDER`).
- **BFG missed secret**: ensure replacements file matches exact string, rerun, verify with `git log -p`.
- **Docs broken links**: `rg -n "old/path" -g"*.md"` to update references.
- **Slow pre-commit**: scope hooks with `files:` patterns or use `--files` overrides.

______________________________________________________________________

### References

- [Gitleaks Documentation](https://github.com/gitleaks/gitleaks)
- [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/)
- [ADR Best Practices](https://adr.github.io/)

______________________________________________________________________

**Next Actions:**

1. Commit this playbook and supporting scripts.
1. Schedule first interactive cleanup session using the procedures above.
1. Track outputs in `.security-backups/scan-results/` for auditability.
