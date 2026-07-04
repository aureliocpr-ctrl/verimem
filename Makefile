# HippoAgent — common dev tasks.
#
# `make help` lists all targets. Designed to work on Linux / macOS / Git-Bash.
# PowerShell users: prefer `python -m <tool>` invocations directly.

PY ?= python
PIP ?= $(PY) -m pip
PKG := hippoagent

.PHONY: help install install-dev install-full lint lint-fix \
        typecheck test cov sec-ruff sec-bandit sec-audit sec \
        build clean docker-build docker-run release-dry \
        wheel sdist smoke \
        bench-mock bench-real bench-skill bench-memory bench-summary \
        bench-ablation bench-compare bench-clean bench-help bench-all \
        bench-quick bench-csv ci ci-fast stats

help: ## Show this help.
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_\-]+:.*?## / {printf "  %-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ─── install ─────────────────────────────────────────────────────
install: ## Install package (minimal core).
	$(PIP) install -e .

install-dev: ## Install package + dev tools.
	$(PIP) install -e ".[dev]"

install-full: ## Install everything (vision + tui + mcp + dev).
	$(PIP) install -e ".[full,dev]"

# ─── quality ─────────────────────────────────────────────────────
lint: ## Run ruff (lint).
	$(PY) -m ruff check $(PKG) tests scripts

lint-fix: ## Run ruff with --fix.
	$(PY) -m ruff check --fix $(PKG) tests scripts

typecheck: ## Run mypy if configured (best-effort).
	-$(PY) -m mypy $(PKG) || true

test: ## Run unit tests (offline, mock LLM).
	HIPPO_OFFLINE=1 $(PY) -m pytest -q -m "not slow and not e2e"

stats: ## Print project size + test count + LOC (FORGIA #100).
	@echo "─── HippoAgent stats ─────────────────────"
	@$(PY) -c "import pathlib; root=pathlib.Path('hippoagent'); print(f'  package files: {sum(1 for _ in root.rglob(chr(42)+chr(46)+chr(112)+chr(121)) if \"__pycache__\" not in str(_))}')"
	@$(PY) -c "import pathlib; root=pathlib.Path('tests'); print(f'  test files:    {sum(1 for _ in root.rglob(chr(42)+chr(46)+chr(112)+chr(121)) if \"__pycache__\" not in str(_))}')"
	@$(PY) -c "import pathlib; root=pathlib.Path('scripts'); print(f'  script files:  {sum(1 for _ in root.rglob(chr(42)+chr(46)+chr(112)+chr(121)) if \"__pycache__\" not in str(_))}')"
	@$(PY) -m pytest --collect-only -q --no-header 2>/dev/null | tail -1 | awk '{print "  total tests:   " $$1}'

test-fast: ## Faster test pass: skips real_provider, E2E MCP, bench CLI subprocess tests.
	HIPPO_OFFLINE=1 $(PY) -m pytest -q --tb=no \
	  -k "not real_provider and not e2e_smoke and not bench_cli and not bench_recall_ablation"

cov: ## Run tests with coverage report.
	HIPPO_OFFLINE=1 $(PY) -m pytest --cov=$(PKG) --cov-report=term-missing --cov-report=xml

# ─── security ────────────────────────────────────────────────────
sec-ruff: ## Ruff security rules (S-group).
	$(PY) -m ruff check --select S $(PKG)

sec-bandit: ## Bandit static security scan.
	$(PY) -m bandit -r $(PKG) -ll -i

sec-audit: ## pip-audit on installed deps (HIGH/CRITICAL gate).
	$(PY) -m pip_audit --strict --vulnerability-service osv

sec: sec-ruff sec-bandit sec-audit ## Run the full security suite.

# ─── build / packaging ───────────────────────────────────────────
clean: ## Remove build artefacts and caches.
	rm -rf build dist wheels htmlcov .coverage* coverage.xml coverage.json *.egg-info \
	       .pytest_cache .mypy_cache .ruff_cache .benchmarks .hypothesis

build: clean ## Build sdist + wheel into dist/.
	$(PY) -m build

wheel: ## Build wheel only.
	$(PY) -m build --wheel

sdist: ## Build source distribution only.
	$(PY) -m build --sdist

smoke: ## Verify a clean install + the entry-points run.
	$(PIP) uninstall -y $(PKG) || true
	$(PIP) install .
	engram --help
	hippo --help

# ─── multi-model bench (FORGIA #27) ──────────────────────────────
bench-quick: ## Bench harness mock + 2 tasks only (fast smoke for `make ci`).
	HIPPO_OFFLINE=1 $(PY) scripts/bench_with_without_hippo.py --providers mock --quiet --max-tasks 2

bench-mock: ## Bench harness on MockLLM only (always works, deterministic).
	HIPPO_OFFLINE=1 $(PY) scripts/bench_with_without_hippo.py --providers mock

bench-real: ## Bench harness on every provider with an API key set.
	$(PY) scripts/bench_with_without_hippo.py --providers auto

bench-skill: ## Bench `skill_compounding` suite (8 digit-sum tasks).
	$(PY) scripts/bench_with_without_hippo.py --suite skill_compounding --providers auto

bench-memory: ## Bench `memory_recall` suite (3 seed + 3 query — discriminative).
	$(PY) scripts/bench_with_without_hippo.py --suite memory_recall --providers auto

bench-summary: ## Render the latest bench summary as markdown.
	$(PY) scripts/bench_summary_md.py

bench-csv: ## Render the latest bench summary as CSV (Excel-friendly).
	$(PY) scripts/bench_summary_md.py --csv

bench-ablation: ## Recall pipeline ablation study (no LLM calls, ~300 ms).
	$(PY) scripts/bench_recall_ablation.py

bench-compare: ## Diff two bench summary JSON: BEFORE=path AFTER=path.
	$(PY) scripts/bench_compare.py $(BEFORE) $(AFTER)

bench-clean: ## Dry-run list of transient bench dirs in tempdir (--apply to delete).
	$(PY) scripts/clean_bench_data.py $(if $(APPLY),--apply)

bench-all: ## Run every suite on auto-detected providers (the heavy nightly).
	$(PY) scripts/bench_with_without_hippo.py --suite default --providers auto --save-md
	$(PY) scripts/bench_with_without_hippo.py --suite skill_compounding --providers auto --save-md
	$(PY) scripts/bench_with_without_hippo.py --suite memory_recall --providers auto --save-md
	$(PY) scripts/bench_with_without_hippo.py --suite hard_memory_recall --providers auto --save-md

bench-help: ## Print available bench suites + headline result per suite.
	@echo "Available task suites (--suite <name>):"
	@echo ""
	@echo "  default              5 trivia tasks; transport / harness check."
	@echo "                       Raw 100% wins (overhead is the cost of HippoAgent)."
	@echo ""
	@echo "  skill_compounding    8 digit-sum tasks; tests procedural compilation."
	@echo "                       Raw 100% but anthropic hippo_warm latency -41% vs cold."
	@echo ""
	@echo "  memory_recall        3 seed + 3 query; tests long-term memory itself."
	@echo "                       Raw 0.50, hippo 1.00 across providers (+50pp)."
	@echo ""
	@echo "  hard_memory_recall   12 tasks (direct + paraphrased + synthesis)."
	@echo "                       Raw 0.50, hippo 0.92-1.00 (DeepSeek loses synthesis)."

# ─── ci shortcut ─────────────────────────────────────────────────
ci-fast: lint test ## Lint + tests, no bench.

ci: lint test bench-mock bench-ablation ## Full local CI: lint + tests + mock-bench + ablation.

# ─── docker ──────────────────────────────────────────────────────
docker-build: ## Build the runtime image (multi-stage).
	docker build -t hippoagent:dev .

docker-run: ## Run the dashboard on 127.0.0.1:8765 (loopback only).
	docker run --rm -p 127.0.0.1:8765:8765 -v $(PWD)/data:/app/data hippoagent:dev

# ─── release ─────────────────────────────────────────────────────
release-dry: ## Dry-run a release (set V=X.Y.Z).
	$(PY) scripts/release.py $(V) --dry-run --no-push
