---
name: update-arch-system
description: Securely update an Arch Linux system with yay, including official repositories and AUR packages. Use when asked to update or upgrade Arch, run yay system upgrades, inspect pending AUR updates, assess PKGBUILD or software supply-chain risk, or handle sudo safely from an agent terminal or graphical askpass dialog.
---

# Update Arch System

Update the whole Arch system without treating AUR recipes as trusted packages. Inspect first, install second, and never accept or expose a password in chat, logs, command arguments, or piped stdin.

## Preconditions

1. Confirm Arch and required tools:

   ```bash
   test -r /etc/arch-release
   command -v pacman yay git curl
   ```

2. Preserve a full-upgrade transaction. Never use `pacman -Sy`, install a subset of repository updates, disable signature checking, or edit pacman trust settings.
3. Explain that an AUR review reduces risk but cannot prove that software is secure.
4. Check for the optional [arch-mcp](references/arch-mcp.md) server and record whether this run uses the arch-mcp or CLI path for each step.
5. Ensure `checkupdates` is available, following [Bootstrap checkupdates](#bootstrap-checkupdates). It permits update discovery without sudo, so the audit can finish before any password prompt.

### Bootstrap checkupdates

`checkupdates` ships in `pacman-contrib`. Install it when missing rather than leaving the user a manual task.

1. Detect it with `command -v checkupdates`, or by catching a `CommandNotFound` error from `check_updates_dry_run`.
2. Confirm it resolves from an official repository before installing anything, with `get_official_package_info` or `pacman -Si pacman-contrib`. Never satisfy this dependency from the AUR.
3. Choose one of two routes, both of which avoid a partial upgrade. Never use `-Sy` for either.
   - **Immediate**, when `check_database_freshness` or the sync database timestamps show the databases are not ahead of the installed packages: install now with `install_package_secure(package_name='pacman-contrib', confirm=true)`, or `sudo pacman -S --needed pacman-contrib` using the sudo method in [references/aur-review.md](references/aur-review.md). This costs one password prompt but enables sudo-free discovery on this run.
   - **Deferred**, when the databases are already ahead of the installed system, so a standalone install would pull newer dependencies: do not install it on its own. Add it to the full upgrade in [Install](#install) as `yay -Syu pacman-contrib`. The benefit then starts on the next run.
4. Report which route was taken and why. This step changes the system, so never do it silently.
5. Never block on it. If no secure sudo method exists, or the install fails, continue with the CLI discovery fallback and finish the audit.

## Check Arch news

Arch announces upgrades that require manual intervention. Applying one of those upgrades unprepared is a common way to break a system, so this gate runs before anything is installed.

1. Retrieve current announcements with `fetch_news(action='critical', limit=30)` and `fetch_news(action='since_update')`. `limit` bounds the items scanned, not the critical items returned, so keep it generous. Without arch-mcp, fetch `https://archlinux.org/feeds/news/` and read every item published after the last `pacman -Syu` recorded in `/var/log/pacman.log`.
2. The feed carries only about ten items on either path. If the last full upgrade predates the oldest item, say so and point the user at the [Arch news archive](https://archlinux.org/news/) for the uncovered period. An unreachable window is not the same as no news.
3. For each item describing manual intervention or a breaking change, read the linked announcement and consult the Arch Wiki with `search_archwiki` for the affected component.
4. Cross-reference each such item against the pending upgrades from [Discover updates](#discover-updates), resolving the pending set first if needed. **Stop and request explicit approval** when an item names a pending package, or when the affected packages cannot be determined with confidence. Present the title, link, affected packages, and required manual steps, and let the user carry out the intervention before continuing.
5. If no critical news applies to the pending set, say so explicitly.

## Discover updates

1. Enumerate official repository updates without sudo:

   ```bash
   checkupdates
   ```

   Prefer `check_database_freshness` followed by `check_updates_dry_run`, which wraps the same command. `checkupdates` syncs into a temporary database and does not touch the system databases.

2. If `checkupdates` is unavailable because the bootstrap was deferred or skipped, refresh the databases without installing, using the sudo method in [references/aur-review.md](references/aur-review.md):

   ```bash
   yay -Syu --print
   ```

   Treat exit 1 with no listed targets as “no updates”; treat authentication, network, keyring, mirror, or dependency errors as failures. When reporting from an unrefreshed `pacman -Qu`, state the database age and mark the results provisional until the refresh.

3. Enumerate AUR upgrades, which needs no sudo on either path:

   ```bash
   yay -Qua
   ```

4. Report packages that are orphaned, flagged out of date, missing from AUR, or replaced. Do not confuse “flagged out of date” with maliciousness, but include it in the review context.
5. If no AUR upgrades are pending, say so explicitly and skip the AUR audit.

## Audit every AUR target

Read [references/aur-review.md](references/aur-review.md) completely before handling any pending AUR target.

1. Resolve each target's `PackageBase` and current metadata with the AUR RPC, or with `audit_package_security(action='metadata_risk')` and `search_aur`. Clone `https://aur.archlinux.org/<PackageBase>.git` into a new `mktemp -d` directory. Never source the `PKGBUILD` or run `makepkg` yet.
2. Record the audited Git commit. Inspect `PKGBUILD`, `.SRCINFO`, `.install` files, patches, and every other tracked build input. Compare with the recipe that produced the installed version when it can be recovered from yay's cache or AUR Git history.
3. Run the scanner bundled with this skill against the clone:

   ```bash
   scripts/scan-aur-recipe.sh /path/to/package-base
   ```

   Resolve the script against this skill's own directory. Where arch-mcp is available, also run `audit_package_security(action='pkgbuild_analysis')` on the `PKGBUILD` read from the disposable clone at the audited commit. That analysis sees PKGBUILD text only, so it supplements the bundled scanner and never replaces it. Feed the union of both results into the risk decision.

4. Check with `get_official_package_info` or `pacman -Si` whether the package now exists in an official repository, and report the migration as a safer alternative if it does.
5. Verify provenance, immutable source references, hashes/signatures, maintainer/orphan state, dependency changes, build functions, hooks, and unusual comments or history. Only after static inspection may `makepkg --verifysource` be used to fetch and validate sources.
6. Assign a risk level using the reference. Continue automatically only for **low** risk. Pause for explicit approval on **medium**, **high**, uncertainty, or an unreviewed new AUR dependency. Recommend rejection for high risk and require a package-specific override to continue.

## Install

This step is deliberately CLI-only. See the unused tools listed in [references/arch-mcp.md](references/arch-mcp.md).

1. Recheck each AUR repository's remote HEAD immediately before installation. If it differs from the audited commit, abort and repeat the review. Keep yay's diff review enabled and verify that its fetched recipe matches the reviewed change before approving the build.
2. Run the full upgrade with `yay -Syu` using an attached terminal or graphical askpass, appending `pacman-contrib` if its bootstrap was deferred. Do not use `--noconfirm` when AUR packages are involved. Audit any newly proposed AUR dependency before allowing the transaction to continue.
3. Allow pacman to enforce keyring, signature, integrity, conflict, and disk-space checks. Stop on any failure rather than bypassing it.

## Verify and report

1. Re-run `pacman -Qu` and `yay -Qua`.
2. Check the system's post-upgrade state with `run_system_health_check`, `diagnose_system(action='failed_services')`, `query_package_history(query_type='failures')`, and `manage_orphans(action='list')`. Without arch-mcp use `systemctl --failed`, `grep -iE 'error|warning' /var/log/pacman.log`, and `pacman -Qdtq`. Only list orphans; never remove them here.
3. Determine whether a reboot is needed by comparing the running kernel from `uname -r` against the installed kernel version, and identify upgraded packages that own running services needing a restart.
4. Report installed versions, residual updates, warnings, failed hooks, packages requiring a reboot or service restart, the risk decision for each AUR target, and whether each check used the arch-mcp or CLI path.
5. Never claim the system is fully updated if either verification command reports an update or fails unexpectedly.
