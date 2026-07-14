.PHONY: install install-global dev test lint doctor stats help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install ai-helper (project-local)
	uv sync --extra dev

install-global: ## Install ai-helper globally (use from any directory)
	uv tool install -e . --force

dev: install ## Install + run doctor to verify setup
	uv run ai-helper doctor

test: ## Run all tests
	uv run pytest -v

lint: ## Run linter
	uv run ruff check src/ tests/

lint-fix: ## Auto-fix lint issues
	uv run ruff check --fix src/ tests/

doctor: ## Health check across AI tools
	uv run ai-helper doctor

stats: ## Show usage stats (last 7 days)
	uv run ai-helper stats

stats-today: ## Show today's usage stats
	uv run ai-helper stats --period 1d

config: ## Show AI tool configuration
	uv run ai-helper config show

optimize: ## Show optimization status
	uv run ai-helper optimize status

clean: ## Remove build artifacts
	rm -rf dist/ build/ *.egg-info .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
