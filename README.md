# ai-skills — Public AI Agent Skills

A public home for the AI agent skills I write for my own workflow and consider worth sharing.
Today it holds one: updating Arch Linux without blindly trusting AUR recipes. It is here because
it may be useful to other people with the same problem, not because it was designed as a
general-purpose library.

Each skill is a self-contained directory with a `SKILL.md`, its helper scripts, and unit tests.
A generic [`Makefile`](Makefile) symlinks them into whichever agent harnesses you use — Claude
Code, Codex, Google Antigravity, or a plain `.agents` directory.

---

## 🧩 The Skills

### `update-arch-system`
- **Description**: Securely update an Arch Linux system with `yay`, covering both official repositories and the AUR, without treating AUR recipes as trusted packages.
- **Useful if you**: run Arch with `yay` and want every pending AUR recipe statically reviewed *before* any of its code executes on your machine.
- **Key Features**:
  - Audit before install: every pending AUR target is reviewed statically before any package code runs.
  - Bundled supply-chain scanner ([`scripts/scan-aur-recipe.sh`](update-arch-system/scripts/scan-aur-recipe.sh)) exiting `0` clean / `1` medium findings / `2` high findings.
  - Low / medium / high risk gate — only **low** proceeds automatically; medium and high require explicit approval.
  - Review/install race prevention by re-checking the AUR remote HEAD against the audited commit.
  - Blocking Arch news gate — an announcement requiring manual intervention stops the upgrade until you have handled it.
  - Passwords are never accepted in chat, arguments, or piped stdin — only an attached terminal or a graphical askpass helper.
  - Optional [arch-mcp](https://github.com/iht/arch-mcp) integration for news gating, Arch Wiki research, a second PKGBUILD analysis, and post-upgrade health checks. Every step keeps a plain-CLI fallback, so the skill works without the server.

### ⚠️ Caveats

This was written against one Linux setup and is shared as-is. Before trusting it on your machine,
note that it assumes:

- `pacman` + `yay` on Arch (it will not work anywhere else);
- that it may install `pacman-contrib`, which provides `checkupdates` and lets it enumerate
  updates without sudo. It is pulled from the official repositories, either on its own or folded
  into the upgrade transaction, never as a partial upgrade;
- `python3`, and `uv` or `pytest`, for the bundled test suite.

Read the `SKILL.md` and the scripts before running anything that touches your package manager.
Adapt the paths to fit your own environment.

---

## 🚀 Getting Started

```bash
git clone git@github.com:herraiz-org/ai-skills.git
cd ai-skills

make build      # lint + validate metadata + run the test suites
make install    # symlink every skill into all four harnesses
```

Optional tooling: [`uv`](https://docs.astral.sh/uv/) (preferred test runner — it pulls the Python
dependencies automatically; otherwise `pytest` or `unittest` is used) and `shellcheck` (falls back
to `bash -n` when absent).

Skills are discovered by wildcard — any directory containing a `SKILL.md` is picked up, with no
registration step.

---

## 📦 Installation & Management

| Command | Action | Destination Directory |
| :--- | :--- | :--- |
| `make install` / `make install-all` | Symlink skills to AGY, Claude Code, Codex, and `.agents` | Configured targets below |
| `make install-agy` | Link skills to Google Antigravity (AGY) | `~/.gemini/config/skills` |
| `make install-claude` | Link skills to Claude Code | `~/.claude/skills` |
| `make install-codex` | Link skills to Codex | `~/.codex/skills` |
| `make install-agents` | Link skills to `.agents` | `~/.agents/skills` |
| `make uninstall` / `make uninstall-all` | Remove symlinks from all installed harnesses | — |

Destinations are plain variables, so override any of them if your harness lives elsewhere:

```bash
make install-claude CLAUDE_SKILLS_DIR=~/somewhere/else/skills
```

The same applies to `AGY_SKILLS_DIR`, `CODEX_SKILLS_DIR`, and `AGENTS_SKILLS_DIR`.

---

## 🛠️ Development & Quality Assurance

Commands for testing, linting, and validating skill metadata:

```bash
# Validate SKILL.md YAML frontmatter across all skills
make validate

# Run syntax linting on Python scripts, shell scripts, and skill metadata
make lint

# Run unit tests across all skill directories using uv, pytest, or unittest
make test

# Complete build check (runs linting, validation, and unit tests)
make build

# Clean python bytecode and test cache directories
make clean
```

---

## ➕ Adding Your Own Skill

The repository layout is the only convention — there is nothing to register.

1. Create a `<skill-name>/` directory with a `SKILL.md` whose YAML frontmatter has at least
   `name:` and `description:` (exactly what `make validate` checks):

   ```markdown
   ---
   name: my-skill
   description: One sentence stating what it does and when an agent should reach for it.
   ---
   ```

2. Follow the layout used by [`update-arch-system/`](update-arch-system):
   - `scripts/` — executables the skill invokes
   - `tests/` — `test_*.py` unit tests
   - `references/` — longer documentation the skill loads on demand
   - `agents/` — optional per-harness agent definitions

3. Run `make build` before committing.

---

## 📄 License

Licensed under the Apache License, Version 2.0. See [`LICENSE`](LICENSE) for the full text.
