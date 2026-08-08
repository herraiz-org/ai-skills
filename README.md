# ai-skills — Public AI Agent Skills

[![skills.sh](https://skills.sh/b/herraiz-org/ai-skills)](https://skills.sh/herraiz-org/ai-skills)
[![CI](https://github.com/herraiz-org/ai-skills/actions/workflows/ci.yml/badge.svg)](https://github.com/herraiz-org/ai-skills/actions/workflows/ci.yml)

A public home for the AI agent skills I write for my own workflow and consider worth sharing.
Today it holds one: updating Arch Linux without blindly trusting AUR recipes. It is here because
it may be useful to other people with the same problem, not because it was designed as a
general-purpose library.

Each skill is a self-contained directory under [`skills/`](skills) with a `SKILL.md`, its helper
scripts, and unit tests. Install them with the [`skills`](https://github.com/vercel-labs/skills)
CLI, which detects the agent harnesses you have — Claude Code, Codex, Cursor, Google Antigravity,
and dozens more:

```bash
npx skills add herraiz-org/ai-skills -g
```

---

## 🧩 The Skills

### `update-arch-system`
- **Description**: Securely update an Arch Linux system with `yay`, covering both official repositories and the AUR, without treating AUR recipes as trusted packages.
- **Useful if you**: run Arch with `yay` and want every pending AUR recipe statically reviewed *before* any of its code executes on your machine.
- **Key Features**:
  - Audit before install: every pending AUR target is reviewed statically before any package code runs.
  - Bundled supply-chain scanner ([`scripts/scan-aur-recipe.sh`](skills/update-arch-system/scripts/scan-aur-recipe.sh)) exiting `0` clean / `1` medium findings / `2` high findings.
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

## 📦 Installation

Everything goes through [`npx skills`](https://github.com/vercel-labs/skills). There is nothing to
clone and no paths to configure — the CLI finds the harnesses installed on your machine and offers
them as targets.

```bash
# See what is in here without installing anything
npx skills add herraiz-org/ai-skills --list

# Install every skill for every detected agent, in your home directory
npx skills add herraiz-org/ai-skills -g

# Or be explicit about skill and agent
npx skills add herraiz-org/ai-skills -s update-arch-system -a claude-code -a codex -g
```

Notes on the flags:

- **Scope.** The default is project scope (`./<agent>/skills/`), which is what you want when a
  skill belongs to one repository. Pass `-g` to install into your home directory instead, which is
  the right choice for `update-arch-system`.
- **Symlink vs copy.** The CLI keeps one canonical copy and symlinks each agent at it, so a single
  `npx skills update` refreshes them all. Add `--copy` where symlinks are not available.
- **Non-interactive.** `-y` skips every prompt, which makes the command usable from CI or a
  dotfiles bootstrap script.

Updating and removing use the skill name, not the repository:

```bash
npx skills update update-arch-system
npx skills remove update-arch-system
npx skills list                       # what is installed, and for which agents
```

`npx add-skill` still works but is the deprecated name; it forwards to `npx skills add`.

---

## 🛠️ Development & Quality Assurance

To work on the skills themselves, clone the repository and use the [`Makefile`](Makefile), which
handles linting, metadata validation, and the test suites — installation is no longer its job.

```bash
git clone git@github.com:herraiz-org/ai-skills.git
cd ai-skills

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

Optional tooling: [`uv`](https://docs.astral.sh/uv/) (preferred test runner — it pulls the Python
dependencies automatically; otherwise `pytest` or `unittest` is used) and `shellcheck` (falls back
to `bash -n` when absent).

The same `make build` runs in GitHub Actions
([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) on every push to `main` and every pull
request, against Python 3.11, 3.12, and 3.13, with `shellcheck` present so the shell linting is
the real thing rather than the `bash -n` fallback. Action versions are kept current by
[Dependabot](.github/dependabot.yml).

To try a working copy before pushing it, point the CLI at the checkout instead of at GitHub:

```bash
npx skills add . --list
```

---

## ➕ Adding Your Own Skill

The repository layout is the only convention — there is nothing to register.

1. Create a `skills/<skill-name>/` directory with a `SKILL.md` whose YAML frontmatter has at least
   `name:` and `description:` (exactly what `make validate` checks, and the only fields the
   `skills` CLI requires):

   ```markdown
   ---
   name: my-skill
   description: One sentence stating what it does and when an agent should reach for it.
   ---
   ```

   `skills/<category>/<skill-name>/` works too — the CLI walks `skills/` three levels deep — but
   `make validate` only globs `skills/*/SKILL.md`, so widen that glob if you add categories.

2. Follow the layout used by [`skills/update-arch-system/`](skills/update-arch-system):
   - `scripts/` — executables the skill invokes
   - `tests/` — `test_*.py` unit tests
   - `references/` — longer documentation the skill loads on demand
   - `agents/` — optional per-harness agent definitions

3. Run `make build` before committing.

---

## 📄 License

Licensed under the Apache License, Version 2.0. See [`LICENSE`](LICENSE) for the full text.
