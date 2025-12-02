# =============================================================================
# Qubinode Navigator Airflow - Makefile
# =============================================================================
# Provides commands for managing Airflow, DAGs, MCP servers, and lineage
#
# Usage: make <target>
# Run 'make help' for available targets

.DEFAULT_GOAL := help

# Configuration
COMPOSE_CMD := podman-compose
AIRFLOW_CONTAINER := airflow_airflow-scheduler_1
AIRFLOW_IMAGE := localhost/qubinode-airflow:2.10.4-python3.12

# =============================================================================
# Help
# =============================================================================
.PHONY: help
help:  ## Show this help message
	@echo "Qubinode Navigator Airflow - Available Commands"
	@echo "================================================"
	@echo ""
	@echo "Installation:"
	@echo "  install               Full installation (prereqs, build, start)"
	@echo "  uninstall             Stop services and remove containers/volumes"
	@echo "  build                 Build the Airflow container image"
	@echo ""
	@echo "DAG Management:"
	@echo "  clear-dag-cache       Clear DAG cache and force reload"
	@echo "  clear-dag-cache-id    Clear cache for specific DAG (DAG_ID=<dag_id>)"
	@echo "  validate-dags         Validate all DAG syntax"
	@echo "  lint-dags             Lint DAGs for common issues"
	@echo "  list-dags             List all available DAGs"
	@echo ""
	@echo "Service Management:"
	@echo "  up                    Start all services"
	@echo "  down                  Stop all services"
	@echo "  restart               Restart all services"
	@echo "  restart-scheduler     Restart scheduler only (for DAG reload)"
	@echo "  logs                  View logs from all services"
	@echo "  status                Show status of all services"
	@echo ""
	@echo "Testing:"
	@echo "  test-mcp              Test MCP server connectivity"
	@echo "  test-lineage          Test lineage/Marquez connectivity"
	@echo "  health                Check health of all services"
	@echo ""
	@echo "Initialization:"
	@echo "  init-prereqs          Initialize all prerequisites (vault.yml, repos)"
	@echo "  init-db               Initialize/reset Airflow database"
	@echo ""
	@echo "Cleanup:"
	@echo "  clean-logs            Clean old log files"
	@echo "  clean-pycache         Clean Python bytecode cache"

# =============================================================================
# Installation
# =============================================================================
.PHONY: install
install: init-prereqs build up  ## Full installation (prereqs, build, start)
	@echo ""
	@echo "========================================"
	@echo "Installation Complete!"
	@echo "========================================"
	@echo ""
	@echo "Services:"
	@echo "  Airflow UI:    http://localhost:8888 (admin/admin)"
	@echo "  MCP Server:    http://localhost:8889"
	@echo "  Marquez API:   http://localhost:5001"
	@echo "  Marquez Web:   http://localhost:3000"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Access Airflow UI and enable DAGs"
	@echo "  2. Trigger infrastructure deployments"
	@echo "  3. View lineage at Marquez Web UI"
	@echo ""

.PHONY: uninstall
uninstall:  ## Stop services and remove containers/volumes
	@echo "Stopping all services..."
	@$(COMPOSE_CMD) --profile vault down -v 2>/dev/null || true
	@echo ""
	@echo "Removing Airflow container image..."
	@podman rmi $(AIRFLOW_IMAGE) 2>/dev/null || true
	@echo ""
	@echo "Cleaning up logs and cache..."
	@rm -rf logs/dag_processor_manager/* 2>/dev/null || true
	@find dags -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@find dags -name "*.pyc" -delete 2>/dev/null || true
	@echo ""
	@echo "[OK] Uninstall complete"
	@echo ""
	@echo "Note: vault.yml and cloned repositories were NOT removed."
	@echo "To remove them manually:"
	@echo "  rm -f /root/qubinode_navigator/inventories/localhost/group_vars/control/vault.yml"
	@echo "  rm -rf /opt/freeipa-workshop-deployer /opt/kcli-pipelines"

.PHONY: build
build:  ## Build the Airflow container image
	@echo "Building Airflow container image..."
	@$(COMPOSE_CMD) build
	@echo "[OK] Build complete"

# =============================================================================
# DAG Management
# =============================================================================
.PHONY: clear-dag-cache
clear-dag-cache:  ## Clear Airflow DAG cache and force reload
	@echo "Clearing DAG cache..."
	@$(COMPOSE_CMD) exec airflow-scheduler /opt/airflow/scripts/clear-dag-cache.sh || \
		podman exec $(AIRFLOW_CONTAINER) /opt/airflow/scripts/clear-dag-cache.sh || \
		echo "[WARN] Could not execute in container, trying locally..." && \
		./scripts/clear-dag-cache.sh
	@echo ""
	@echo "Restarting scheduler to force reload..."
	@$(COMPOSE_CMD) restart airflow-scheduler 2>/dev/null || \
		podman restart $(AIRFLOW_CONTAINER) 2>/dev/null || true
	@echo "[OK] DAG cache cleared and scheduler restarted"

.PHONY: clear-dag-cache-id
clear-dag-cache-id:  ## Clear cache for specific DAG (usage: make clear-dag-cache-id DAG_ID=freeipa_deployment)
	@if [ -z "$(DAG_ID)" ]; then \
		echo "ERROR: DAG_ID is required"; \
		echo "Usage: make clear-dag-cache-id DAG_ID=<dag_id>"; \
		exit 1; \
	fi
	@echo "Clearing cache for DAG: $(DAG_ID)..."
	@$(COMPOSE_CMD) exec airflow-scheduler /opt/airflow/scripts/clear-dag-cache.sh $(DAG_ID) || \
		podman exec $(AIRFLOW_CONTAINER) /opt/airflow/scripts/clear-dag-cache.sh $(DAG_ID)
	@echo "[OK] Cache cleared for $(DAG_ID)"

.PHONY: validate-dags
validate-dags:  ## Validate all DAG files for syntax errors
	@echo "Validating DAG syntax..."
	@for dag in dags/*.py; do \
		echo -n "Checking $$dag... "; \
		python3 -c "import ast; ast.parse(open('$$dag').read())" 2>/dev/null && echo "[OK]" || echo "[ERROR]"; \
	done
	@echo ""
	@echo "Checking Airflow imports..."
	@python3 -c "from airflow.models import DagBag; db = DagBag('dags'); errors = db.import_errors; print('[OK] No import errors' if not errors else '[ERROR] Import errors: ' + str(errors))"

.PHONY: lint-dags
lint-dags:  ## Lint DAGs for common issues (ADR-0045, ADR-0046 compliance)
	@./scripts/lint-dags.sh dags/

.PHONY: list-dags
list-dags:  ## List all available DAGs
	@$(COMPOSE_CMD) exec airflow-webserver airflow dags list 2>/dev/null || \
		podman exec $(AIRFLOW_CONTAINER) airflow dags list 2>/dev/null || \
		echo "[WARN] Airflow not running, listing DAG files:" && ls -1 dags/*.py

# =============================================================================
# Service Management
# =============================================================================
.PHONY: up
up:  ## Start all services (Airflow + MCP + Lineage)
	@echo "Starting Airflow services..."
	@$(COMPOSE_CMD) up -d
	@echo "[OK] Services started"
	@echo ""
	@echo "Services:"
	@echo "  Airflow UI:    http://localhost:8888"
	@echo "  MCP Server:    http://localhost:8889"
	@echo "  Marquez API:   http://localhost:5001"
	@echo "  Marquez Web:   http://localhost:3000"

.PHONY: up-vault
up-vault:  ## Start all services including HashiCorp Vault
	@echo "Starting Airflow with Vault..."
	@$(COMPOSE_CMD) --profile vault up -d
	@echo "[OK] Services started with Vault"
	@echo ""
	@echo "Services:"
	@echo "  Airflow UI:    http://localhost:8888"
	@echo "  MCP Server:    http://localhost:8889"
	@echo "  Marquez API:   http://localhost:5001"
	@echo "  Marquez Web:   http://localhost:3000"
	@echo "  Vault:         http://localhost:8200"

.PHONY: down
down:  ## Stop all services
	@echo "Stopping all services..."
	@$(COMPOSE_CMD) --profile lineage --profile mcp --profile vault down
	@echo "[OK] Services stopped"

.PHONY: restart
restart:  ## Restart all services
	@echo "Restarting all services..."
	@$(COMPOSE_CMD) restart
	@echo "[OK] Services restarted"

.PHONY: restart-scheduler
restart-scheduler:  ## Restart scheduler only (for DAG reload)
	@echo "Restarting Airflow scheduler..."
	@$(COMPOSE_CMD) restart airflow-scheduler
	@echo "[OK] Scheduler restarted"

.PHONY: logs
logs:  ## View logs from all services
	@$(COMPOSE_CMD) logs -f

.PHONY: status
status:  ## Show status of all services
	@echo "Service Status:"
	@echo "==============="
	@$(COMPOSE_CMD) ps
	@echo ""
	@echo "Health Checks:"
	@echo "=============="
	@curl -s http://localhost:8888/health 2>/dev/null && echo " - Airflow Webserver: [OK]" || echo " - Airflow Webserver: [DOWN]"
	@curl -s http://localhost:8889/sse 2>/dev/null && echo " - MCP Server: [OK]" || echo " - MCP Server: [DOWN/DISABLED]"
	@curl -s http://localhost:5001/api/v1/namespaces 2>/dev/null && echo " - Marquez API: [OK]" || echo " - Marquez API: [DOWN/DISABLED]"

# =============================================================================
# Testing
# =============================================================================
.PHONY: test-mcp
test-mcp:  ## Test MCP server connectivity
	@echo "Testing MCP server..."
	@curl -s http://localhost:8889/sse 2>/dev/null | head -5 && \
		echo "[OK] MCP server is responding" || \
		echo "[ERROR] MCP server not responding (is it enabled?)"

.PHONY: test-lineage
test-lineage:  ## Test lineage/Marquez connectivity
	@echo "Testing Marquez API..."
	@curl -s http://localhost:5001/api/v1/namespaces 2>/dev/null | python3 -m json.tool 2>/dev/null && \
		echo "[OK] Marquez is responding" || \
		echo "[ERROR] Marquez not responding (is lineage profile enabled?)"

.PHONY: health
health:  ## Check health of all services
	@echo "Health Check Results"
	@echo "===================="
	@echo ""
	@echo -n "PostgreSQL: "
	@pg_isready -h localhost -U airflow 2>/dev/null && echo "[OK]" || echo "[DOWN]"
	@echo -n "Airflow Webserver: "
	@curl -sf http://localhost:8888/health >/dev/null && echo "[OK]" || echo "[DOWN]"
	@echo -n "Airflow Scheduler: "
	@$(COMPOSE_CMD) exec airflow-scheduler airflow jobs check --job-type SchedulerJob 2>/dev/null && echo "[OK]" || echo "[DOWN]"
	@echo -n "MCP Server: "
	@curl -sf http://localhost:8889/sse >/dev/null && echo "[OK]" || echo "[DOWN/DISABLED]"
	@echo -n "Marquez API: "
	@curl -sf http://localhost:5001/api/v1/namespaces >/dev/null && echo "[OK]" || echo "[DOWN/DISABLED]"

# =============================================================================
# Initialization
# =============================================================================
.PHONY: init-prereqs
init-prereqs:  ## Initialize all prerequisites (vault.yml, repositories)
	@echo "Initializing prerequisites..."
	@./scripts/init-prerequisites.sh
	@echo "[OK] Prerequisites initialized"

.PHONY: init-db
init-db:  ## Initialize/reset Airflow database
	@echo "Initializing Airflow database..."
	@$(COMPOSE_CMD) run --rm airflow-init
	@echo "[OK] Database initialized"

# =============================================================================
# Cleanup
# =============================================================================
.PHONY: clean-logs
clean-logs:  ## Clean old log files (older than 7 days)
	@echo "Cleaning old logs..."
	@find logs -name "*.log" -mtime +7 -delete 2>/dev/null || true
	@find logs -type d -empty -delete 2>/dev/null || true
	@echo "[OK] Old logs cleaned"

.PHONY: clean-pycache
clean-pycache:  ## Clean Python bytecode cache
	@echo "Cleaning Python bytecode cache..."
	@find dags -name "*.pyc" -delete 2>/dev/null || true
	@find dags -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@echo "[OK] Bytecode cache cleaned"
