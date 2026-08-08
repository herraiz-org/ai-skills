# Generic Makefile for Managing AI Agent Skills

SKILL_FILES := $(wildcard skills/*/SKILL.md)
SKILLS      := $(patsubst %/SKILL.md,%,$(SKILL_FILES))

.PHONY: all help test validate lint lint-skills lint-python lint-shell build clean

all: help

help:
	@echo "Agent Skills Repository Management Makefile"
	@echo "-------------------------------------------"
	@echo "Discovered skills: $(SKILLS)"
	@echo ""
	@echo "Installing is not a Make target. Use the skills CLI:"
	@echo "  npx skills add herraiz-org/ai-skills -g"
	@echo ""
	@echo "Targets:"
	@echo "  make test               Run unit test suites across all skill directories"
	@echo "  make validate           Validate skill metadata (SKILL.md frontmatter)"
	@echo "  make lint               Run linting on python scripts, shell scripts, and skill metadata"
	@echo "  make build              Run linting, validation, and test suite"
	@echo "  make clean              Remove Python bytecode and test cache artifacts"
	@echo ""

validate: lint-skills

lint-skills:
	@echo "==> Validating skill metadata..."
	@errors=0; \
	for skill in $(SKILLS); do \
		skill_md="$$skill/SKILL.md"; \
		if [ ! -f "$$skill_md" ]; then \
			echo "[!] Error: $$skill is missing SKILL.md"; \
			errors=$$((errors+1)); \
		else \
			if ! grep -q "^name:" "$$skill_md"; then \
				echo "[!] Error: $$skill_md missing 'name:' field in frontmatter"; \
				errors=$$((errors+1)); \
			fi; \
			if ! grep -q "^description:" "$$skill_md"; then \
				echo "[!] Error: $$skill_md missing 'description:' field in frontmatter"; \
				errors=$$((errors+1)); \
			fi; \
		fi; \
	done; \
	if [ $$errors -gt 0 ]; then \
		echo "[!] Skill validation failed with $$errors error(s)."; \
		exit 1; \
	else \
		echo "[✓] All skills validated successfully."; \
	fi

lint-python:
	@echo "==> Checking Python script syntax..."
	@py_files=$$(find . -name "*.py" -not -path "*/.*"); \
	if [ -n "$$py_files" ]; then \
		python3 -m py_compile $$py_files && echo "[✓] Python syntax check passed."; \
	else \
		echo "No Python files found."; \
	fi

lint-shell:
	@echo "==> Checking shell script syntax..."
	@sh_files=$$(find . -name "*.sh" -not -path "*/.*"); \
	if [ -z "$$sh_files" ]; then \
		echo "No shell scripts found."; \
	elif command -v shellcheck >/dev/null 2>&1; then \
		shellcheck $$sh_files && echo "[✓] Shellcheck passed."; \
	else \
		for f in $$sh_files; do bash -n "$$f" || exit 1; done; \
		echo "[✓] bash -n syntax check passed (shellcheck not installed)."; \
	fi

lint: lint-skills lint-python lint-shell

test:
	@echo "==> Running tests across skills..."
	@if command -v uv >/dev/null 2>&1; then \
		uv run --with pytest pytest; \
	elif command -v pytest >/dev/null 2>&1; then \
		pytest; \
	else \
		find . -type d -name "tests" -exec python3 -m unittest discover -s {} -p "test_*.py" -v \; ; \
	fi

build: lint test
	@echo "==> Build check complete."

clean:
	@echo "==> Cleaning cache and temporary files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -type d -name ".pytest_cache" -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete
	@echo "[✓] Clean complete."
