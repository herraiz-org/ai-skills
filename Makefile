# Generic Makefile for Managing AI Agent Skills

SKILL_FILES := $(wildcard */SKILL.md)
SKILLS      := $(patsubst %/SKILL.md,%,$(SKILL_FILES))

# Harness Skill Destination Directories (override via environment or CLI flag)
AGY_SKILLS_DIR    ?= $(HOME)/.gemini/config/skills
CLAUDE_SKILLS_DIR ?= $(HOME)/.claude/skills
CODEX_SKILLS_DIR  ?= $(HOME)/.codex/skills
AGENTS_SKILLS_DIR ?= $(HOME)/.agents/skills

.PHONY: all help install install-all install-agy install-claude install-codex install-agents \
        uninstall uninstall-all uninstall-agy uninstall-claude uninstall-codex uninstall-agents \
        test validate lint lint-skills lint-python lint-shell build clean

all: help

help:
	@echo "Agent Skills Repository Management Makefile"
	@echo "-------------------------------------------"
	@echo "Discovered skills: $(SKILLS)"
	@echo ""
	@echo "Targets:"
	@echo "  make install            Install skills into agy, claude code, codex, and .agents"
	@echo "  make install-agy        Install skills to AGY ($(AGY_SKILLS_DIR))"
	@echo "  make install-claude     Install skills to Claude Code ($(CLAUDE_SKILLS_DIR))"
	@echo "  make install-codex      Install skills to Codex ($(CODEX_SKILLS_DIR))"
	@echo "  make install-agents     Install skills to .agents ($(AGENTS_SKILLS_DIR))"
	@echo ""
	@echo "  make uninstall          Uninstall skills from agy, claude code, codex, and .agents"
	@echo "  make uninstall-agy      Uninstall skills from AGY"
	@echo "  make uninstall-claude   Uninstall skills from Claude Code"
	@echo "  make uninstall-codex    Uninstall skills from Codex"
	@echo "  make uninstall-agents   Uninstall skills from .agents"
	@echo ""
	@echo "  make test               Run unit test suites across all skill directories"
	@echo "  make validate           Validate skill metadata (SKILL.md frontmatter)"
	@echo "  make lint               Run linting on python scripts, shell scripts, and skill metadata"
	@echo "  make build              Run linting, validation, and test suite"
	@echo "  make clean              Remove Python bytecode and test cache artifacts"
	@echo ""

install: install-all

install-all: install-agy install-claude install-codex install-agents

install-agy:
	@echo "==> Installing skills to AGY ($(AGY_SKILLS_DIR))..."
	@mkdir -p "$(AGY_SKILLS_DIR)"
	@for skill in $(SKILLS); do \
		echo "    Linking $$skill -> $(AGY_SKILLS_DIR)/$$skill"; \
		ln -sfn "$(CURDIR)/$$skill" "$(AGY_SKILLS_DIR)/$$skill"; \
	done
	@echo "[✓] AGY skill installation complete."

install-claude:
	@echo "==> Installing skills to Claude Code ($(CLAUDE_SKILLS_DIR))..."
	@mkdir -p "$(CLAUDE_SKILLS_DIR)"
	@for skill in $(SKILLS); do \
		echo "    Linking $$skill -> $(CLAUDE_SKILLS_DIR)/$$skill"; \
		ln -sfn "$(CURDIR)/$$skill" "$(CLAUDE_SKILLS_DIR)/$$skill"; \
	done
	@echo "[✓] Claude Code skill installation complete."

install-codex:
	@echo "==> Installing skills to Codex ($(CODEX_SKILLS_DIR))..."
	@mkdir -p "$(CODEX_SKILLS_DIR)"
	@for skill in $(SKILLS); do \
		echo "    Linking $$skill -> $(CODEX_SKILLS_DIR)/$$skill"; \
		ln -sfn "$(CURDIR)/$$skill" "$(CODEX_SKILLS_DIR)/$$skill"; \
	done
	@echo "[✓] Codex skill installation complete."

install-agents:
	@echo "==> Installing skills to Agents ($(AGENTS_SKILLS_DIR))..."
	@mkdir -p "$(AGENTS_SKILLS_DIR)"
	@for skill in $(SKILLS); do \
		echo "    Linking $$skill -> $(AGENTS_SKILLS_DIR)/$$skill"; \
		ln -sfn "$(CURDIR)/$$skill" "$(AGENTS_SKILLS_DIR)/$$skill"; \
	done
	@echo "[✓] Agents skill installation complete."

uninstall: uninstall-all

uninstall-all: uninstall-agy uninstall-claude uninstall-codex uninstall-agents

uninstall-agy:
	@echo "==> Uninstalling skills from AGY ($(AGY_SKILLS_DIR))..."
	@for skill in $(SKILLS); do \
		if [ -L "$(AGY_SKILLS_DIR)/$$skill" ] || [ -e "$(AGY_SKILLS_DIR)/$$skill" ]; then \
			echo "    Removing $(AGY_SKILLS_DIR)/$$skill"; \
			rm -rf "$(AGY_SKILLS_DIR)/$$skill"; \
		fi; \
	done
	@echo "[✓] AGY skill uninstallation complete."

uninstall-claude:
	@echo "==> Uninstalling skills from Claude Code ($(CLAUDE_SKILLS_DIR))..."
	@for skill in $(SKILLS); do \
		if [ -L "$(CLAUDE_SKILLS_DIR)/$$skill" ] || [ -e "$(CLAUDE_SKILLS_DIR)/$$skill" ]; then \
			echo "    Removing $(CLAUDE_SKILLS_DIR)/$$skill"; \
			rm -rf "$(CLAUDE_SKILLS_DIR)/$$skill"; \
		fi; \
	done
	@echo "[✓] Claude Code skill uninstallation complete."

uninstall-codex:
	@echo "==> Uninstalling skills from Codex ($(CODEX_SKILLS_DIR))..."
	@for skill in $(SKILLS); do \
		if [ -L "$(CODEX_SKILLS_DIR)/$$skill" ] || [ -e "$(CODEX_SKILLS_DIR)/$$skill" ]; then \
			echo "    Removing $(CODEX_SKILLS_DIR)/$$skill"; \
			rm -rf "$(CODEX_SKILLS_DIR)/$$skill"; \
		fi; \
	done
	@echo "[✓] Codex skill uninstallation complete."

uninstall-agents:
	@echo "==> Uninstalling skills from Agents ($(AGENTS_SKILLS_DIR))..."
	@for skill in $(SKILLS); do \
		if [ -L "$(AGENTS_SKILLS_DIR)/$$skill" ] || [ -e "$(AGENTS_SKILLS_DIR)/$$skill" ]; then \
			echo "    Removing $(AGENTS_SKILLS_DIR)/$$skill"; \
			rm -rf "$(AGENTS_SKILLS_DIR)/$$skill"; \
		fi; \
	done
	@echo "[✓] Agents skill uninstallation complete."

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
