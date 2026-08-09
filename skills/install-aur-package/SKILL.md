---
name: install-aur-package
description: Securely install a named package on Arch Linux, checking the official repositories first and statically auditing the AUR recipe and every AUR dependency with yay before any of their code runs. Use when asked to install, add, or build a package on Arch, to install something from the AUR with yay or makepkg, to judge whether an AUR package or PKGBUILD is safe to install, to resolve an ambiguous or possibly typosquatted package name, or to handle sudo safely from an agent terminal or graphical askpass dialog.
---

# Install AUR Package

Install one requested package without treating its AUR recipe, or any recipe it drags in, as a
trusted package. Resolve the name, prefer the official repositories, inspect first, install
second, and never accept or expose a password in chat, logs, command arguments, or piped stdin.

Installing for the first time is a decision to trust software that has never run here, made
without a prior recipe to compare against. Identity and provenance carry the weight that a diff
would otherwise carry.

## Preconditions

1. Confirm Arch and required tools:

   ```bash
   test -r /etc/arch-release
   command -v pacman yay git curl
   ```

2. Record the requested name verbatim. Never silently correct its spelling and never install a
   package the user did not name.
3. Preserve a full-upgrade transaction. Never use `pacman -Sy`, install a subset of repository
   updates, disable signature checking, or edit pacman trust settings.
4. Explain that an AUR review reduces risk but cannot prove that software is secure.
5. Check for the optional [arch-mcp](references/arch-mcp.md) server and record whether this run
   uses the arch-mcp or CLI path for each step.

## Resolve the name

Read [Resolve the requested name](references/aur-review.md#resolve-the-requested-name) before
this step. The requested string is untrusted input, and the AUR lets anyone publish under any
unclaimed name.

1. Check whether it is already installed with `pacman -Qi NAME`. Report the installed version
   and stop unless the user explicitly wants a rebuild or a different provider.
2. Check the official repositories with `get_official_package_info`, or `pacman -Si NAME` and
   `pacman -Ss "^NAME$"`, including packages that provide or replace the name. An official
   package is signed and built by a trusted user, so it needs none of the AUR review. When one
   exists, take [Install from an official repository](#install-from-an-official-repository) and
   skip the audit entirely.
3. Otherwise resolve the name in the AUR with `search_aur` and the RPC queries in the reference.
4. **Stop and request an explicit choice** when there is no exact match, or when several
   plausible candidates exist. Present each with votes, popularity, first-submitted date,
   maintainer, and out-of-date flag. Never auto-pick the highest-ranked result.
5. Treat a name one edit away from a popular or official package, a base that is new relative to
   the project it claims to package, or near-zero adoption for widely used software, as a
   lookalike until shown otherwise. `-bin`, `-git` and `-beta` are ordinary AUR conventions and
   are not lookalikes by themselves.
6. Resolve the target's `PackageBase`, which differs from `pkgname` for split packages. Every
   later step clones, audits, and re-checks the base.

### Install from an official repository

1. Complete [Preflight the system](#preflight-the-system) first: this path installs, so it is
   subject to the same partial-upgrade rule.
2. Install with `install_package_secure(package_name=NAME, confirm=true)`, or with
   `sudo pacman -S --needed NAME` using the sudo method in
   [references/aur-review.md](references/aur-review.md). Note that
   `install_package_secure` performs no database refresh and silently falls back to `sudo -n`;
   see [references/arch-mcp.md](references/arch-mcp.md).
3. Continue at [Verify and report](#verify-and-report). Nothing is cloned and no AUR review runs.

## Preflight the system

Installing one package against sync databases that are ahead of the installed system is the
partial-upgrade trap, and `pacman -Sy` alone is how systems get broken.

1. Enumerate pending updates with `check_updates_dry_run`, or `checkupdates`, which syncs into a
   temporary database and does not touch the system databases. If `checkupdates` is missing, do
   not bootstrap `pacman-contrib` here; fall back to `check_database_freshness`, or to
   `stat -c %y /var/lib/pacman/sync/*.db` with `pacman -Qu`, and mark the result provisional.
2. **Stop when updates are pending.** Report them and recommend running the full upgrade first,
   which the `update-arch-system` skill covers if it is installed. With explicit approval, fold
   this install into that upgrade as `yay -Syu NAME` instead. Never run `-Sy` on its own, and
   never use `--noconfirm`.
3. Run the Arch news gate only when the transaction has become a full upgrade, or when an
   announcement names the requested package or one of its dependencies. Use
   `fetch_news(action='critical', limit=30)` and `fetch_news(action='since_update')`, else the
   `https://archlinux.org/feeds/news/` feed read against the last `pacman -Syu` in
   `/var/log/pacman.log`. Stop and request approval for any item requiring manual intervention.
4. Report free space for the build. AUR builds unpack sources and compile in `~/.cache/yay` or
   the makepkg build directory, and a failed build halfway through a transaction is its own
   problem.

## Audit the target and its AUR dependencies

Read [references/aur-review.md](references/aur-review.md) completely before handling the target.
Every AUR dependency executes its own build code on this machine, so a review that stops at the
requested package reviews almost nothing.

1. Clone `https://aur.archlinux.org/<PackageBase>.git` into a new `mktemp -d` directory and
   record `git rev-parse HEAD`. Never source the `PKGBUILD` or run `makepkg` yet.
2. Inspect `PKGBUILD`, `.SRCINFO`, `.install` files, patches, and every other tracked build
   input. Read the whole `git log --stat` rather than a diff: a first install has no baseline,
   so the history is the evidence of who has controlled this recipe and whether it changed hands.
3. Run the scanner bundled with this skill against the clone:

   ```bash
   scripts/scan-aur-recipe.sh /path/to/package-base
   ```

   It exits `0` clean, `1` medium findings, `2` any high finding. Resolve the script against this
   skill's own directory. Where arch-mcp is available, also run
   `audit_package_security(action='pkgbuild_analysis')` on the `PKGBUILD` read from the
   disposable clone at the audited commit. That analysis sees PKGBUILD text only, so it
   supplements the bundled scanner and never replaces it. Feed the union of both results into the
   risk decision.

4. List what the recipe declares, without executing it:

   ```bash
   scripts/list-recipe-deps.sh /path/to/package-base
   ```

   It reads `.SRCINFO` only and prints `TYPE<TAB>NAME` lines for `depends`, `makedepends`,
   `checkdepends` and `optdepends`, exiting `0` on success, `64` on a usage error, and `66` when
   no readable `.SRCINFO` exists. On `66`, never fall back to sourcing the `PKGBUILD`; report the
   missing `.SRCINFO`, which is itself unusual, and read the arrays by eye.

5. Classify each dependency with `get_official_package_info` or `pacman -Si`. Official
   dependencies need no audit. **Repeat this whole section for every AUR `depends`,
   `makedepends` and `checkdepends`**, keeping a set of visited package bases so cycles
   terminate. `makedepends` run at build time with the user's privileges and are audited the same
   way. Record `optdepends` without auditing them; they are not installed. Report the closure,
   its audited commits, and a risk level per member.
6. Verify provenance, immutable source references, hashes and signatures, maintainer and orphan
   state, adoption, build functions, lifecycle hooks, and AUR comments. Only after static
   inspection may `makepkg --verifysource` be used to fetch and validate sources.
7. Assign a risk level using the reference. The transaction inherits the **highest** level in the
   closure. Continue automatically only for **low**. Pause for explicit approval on **medium**,
   **high**, or uncertainty. Recommend rejection for high risk and require a package-specific
   override to continue. Offer safer alternatives when they exist: an official package, a Flatpak,
   or an upstream binary the user installs outside the package manager.

## Install

This step is deliberately CLI-only. See [references/arch-mcp.md](references/arch-mcp.md) for why
`install_package_secure` cannot do it.

1. Recheck every audited base's remote HEAD with
   `git ls-remote https://aur.archlinux.org/<PackageBase>.git refs/heads/master` immediately
   before installation. If any differs from its audited commit, abort and repeat the review.
2. Run `yay -S NAME`, or `yay -Syu NAME` if [Preflight the system](#preflight-the-system) took
   that route, using an attached terminal or graphical askpass. Keep yay's diff review enabled,
   verify that each fetched recipe matches the audited commit, and do not use `--noconfirm`.
3. Audit any package base yay proposes that was not in the audited closure before allowing the
   transaction to continue. Dependency resolution can introduce one that appeared after the
   review.
4. Allow pacman to enforce keyring, signature, integrity, conflict, and disk-space checks. Stop
   on any failure rather than bypassing it.

## Verify and report

1. Confirm the result with `pacman -Qi NAME`, then check what landed on disk with `pacman -Ql`
   and `verify_package_integrity`, or `pacman -Qkk NAME`.
2. Confirm that packages pulled in as dependencies are marked as such, with
   `manage_install_reason` or `pacman -D --asdeps`, so they stay removable with the target.
3. Check the resulting system state with `diagnose_system(action='failed_services')`,
   `query_package_history(query_type='failures')`, and `run_system_health_check`. Without
   arch-mcp use `systemctl --failed` and `grep -iE 'error|warning' /var/log/pacman.log`.
4. Identify anything the install activated or requires: new systemd units, `.install` hook
   output, users or groups created, and whether a reboot or service restart is needed.
5. Report the installed version, every package in the audited closure with its audited commit and
   risk decision, the evidence behind each non-low verdict, warnings and failed hooks, and
   whether each check used the arch-mcp or CLI path.
6. Never claim the package is installed and healthy if any verification command reports a problem
   or fails unexpectedly.
