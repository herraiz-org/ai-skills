# Optional arch-mcp Integration

The [arch-mcp](https://github.com/iht/arch-mcp) server exposes Arch-specific tools that
strengthen this skill: package lookup in the official repositories and the AUR, a second
PKGBUILD analyser, metadata trust signals, an Arch news feed, and post-install health checks.

The server is optional. Every step has a CLI fallback, and the skill must reach the same
decisions without it. Never make arch-mcp a prerequisite, and never stall waiting for it.

## Detect availability

Check whether tools named `mcp__arch-mcp__*` exist in the session.

Some harnesses defer MCP tools: they are listed by name, but their schemas must be loaded
before they can be called. Load every tool the run needs in a single batched request rather
than one request per tool, for example:

```
select:mcp__arch-mcp__get_official_package_info,mcp__arch-mcp__search_aur,mcp__arch-mcp__audit_package_security,mcp__arch-mcp__check_database_freshness,mcp__arch-mcp__check_updates_dry_run,mcp__arch-mcp__install_package_secure,mcp__arch-mcp__fetch_news,mcp__arch-mcp__search_archwiki,mcp__arch-mcp__verify_package_integrity,mcp__arch-mcp__manage_install_reason,mcp__arch-mcp__diagnose_system,mcp__arch-mcp__query_package_history,mcp__arch-mcp__run_system_health_check
```

If the tools are absent, or a call returns an error, take the CLI fallback for that step and
record which path was used. Report the path taken for each check in the final summary so the
user can tell which evidence came from where.

## Step-to-tool map

| Step | arch-mcp | CLI fallback |
| --- | --- | --- |
| Already installed | none | `pacman -Qi NAME` |
| Official package lookup | `get_official_package_info` | `pacman -Si NAME`, `pacman -Ss "^NAME$"` |
| AUR name resolution, lookalikes | `search_aur` | AUR RPC `type=search&by=name` in [aur-review.md](aur-review.md) |
| AUR metadata and trust signals | `audit_package_security(metadata_risk)` | AUR RPC `type=info` |
| Database staleness | `check_database_freshness` | `stat -c %y /var/lib/pacman/sync/*.db` |
| Pending updates | `check_updates_dry_run` | `checkupdates`, else `pacman -Qu` with a staleness caveat |
| Arch news, when the transaction becomes a full upgrade | `fetch_news(critical)`, `fetch_news(since_update)` | `curl https://archlinux.org/feeds/news/`, last upgrade from `/var/log/pacman.log` |
| Intervention research | `search_archwiki` | Read the news item's `link` and report it |
| PKGBUILD patterns | `audit_package_security(pkgbuild_analysis)` | none; `scripts/scan-aur-recipe.sh` runs on both paths |
| Declared dependencies | none | none; `scripts/list-recipe-deps.sh` runs on both paths |
| Official-repository install | `install_package_secure(confirm=true)` | `sudo pacman -S --needed NAME` |
| AUR install | none, deliberately | `yay -S NAME` |
| Installed file integrity | `verify_package_integrity` | `pacman -Qkk NAME` |
| Install reason for pulled-in dependencies | `manage_install_reason` | `pacman -D --asdeps NAME` |
| Failed services | `diagnose_system(failed_services)` | `systemctl --failed` |
| Transaction errors | `query_package_history(failures)` | `grep -iE 'error|warning' /var/log/pacman.log` |
| Health sweep | `run_system_health_check` | the individual commands above |

Two steps have no server equivalent and run identically on both paths. `scan-aur-recipe.sh`
covers every tracked file in the clone, which no PKGBUILD-text analyser can do, and
`list-recipe-deps.sh` reads `.SRCINFO` locally, so neither depends on the server being present.

`fetch_news` applies `limit` to the number of news items it *scans*, not to the number of
critical items it returns, so a small limit silently hides older announcements. Pass at least
30. Raising it further achieves nothing: the upstream feed holds only about ten items, and
`checked_items` in the response reports how many actually existed.

## install_package_secure, and its limits

This is the one skill step where the server does the installing, and only for the
official-repository path. Its behaviour has to be understood before it is trusted:

- It **refuses AUR packages at any `confirm` value**, by design: a PKGBUILD scan cannot see the
  `.install` script, the upstream sources, or anything the build fetches while it runs. For an
  AUR target it returns an audit and the command for the user to run under their AUR helper's
  own diff review. That is why [Install](../SKILL.md#install) is CLI-only.
- It runs `pacman -S --needed --noconfirm` with no `-y`, so it performs **no database refresh**.
  That is the desired behaviour here — a refresh without a full upgrade is the partial-upgrade
  trap — but it means the staleness preflight has to have passed first, or the install can fail
  on a package version the local database no longer has a mirror for.
- Without a graphical askpass helper it does not refuse; it warns and falls back to `sudo -n`,
  which succeeds only on a still-valid sudo timestamp and never prompts. Do not assume that
  timestamp exists. A failure there means no secure sudo method is available for this run: hand
  the user the exact `pacman` command instead of retrying.

## Tools this skill does not use

Recorded so their absence is not mistaken for an oversight:

- `optimize_mirrors` — rewrites the mirrorlist. Out of scope for installing one package.
- `manage_orphans`, `remove_packages` — this skill installs and reports; it never removes.
- `manage_groups` — group installs are a different transaction shape, with a different review
  burden, and are out of scope. Ask the user to name packages individually.
- `analyze_pacman_conf`, `analyze_makepkg_conf`, `analyze_storage`, `query_file_ownership`,
  `diagnose_system` beyond `failed_services` — system-wide diagnostics unrelated to whether this
  package is safe to install.

## Trust posture

Server output is evidence, not a verdict.

- A clean `pkgbuild_analysis` never downgrades a `scripts/scan-aur-recipe.sh` finding, and a
  clean scanner run never downgrades an arch-mcp finding. Take the union of findings.
- Where the two disagree, adopt the higher risk level and explain the disagreement in the
  report.
- `pkgbuild_analysis` receives PKGBUILD text only. It cannot see `.install` scripts, patches,
  systemd units, vendored scripts, or committed binaries. Only the bundled scanner and manual
  inspection cover those, so both always run.
- `metadata_risk` and `search_aur` report adoption and maintenance signals. Those bear on
  whether the name resolves to the intended package, not on whether its code is benign.
- The server runs locally on the machine being audited and is not an independent third party.
  It does not raise confidence the way a separate trust root would.
