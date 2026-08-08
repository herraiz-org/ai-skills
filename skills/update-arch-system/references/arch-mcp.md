# Optional arch-mcp Integration

The [arch-mcp](https://github.com/iht/arch-mcp) server exposes Arch-specific tools that
strengthen this skill: an Arch news feed, Arch Wiki search, a second PKGBUILD analyser, and
post-upgrade health checks.

The server is optional. Every step has a CLI fallback, and the skill must reach the same
decisions without it. Never make arch-mcp a prerequisite, and never stall waiting for it.

## Detect availability

Check whether tools named `mcp__arch-mcp__*` exist in the session.

Some harnesses defer MCP tools: they are listed by name, but their schemas must be loaded
before they can be called. Load every tool the run needs in a single batched request rather
than one request per tool, for example:

```
select:mcp__arch-mcp__fetch_news,mcp__arch-mcp__search_archwiki,mcp__arch-mcp__check_database_freshness,mcp__arch-mcp__check_updates_dry_run,mcp__arch-mcp__audit_package_security,mcp__arch-mcp__get_official_package_info,mcp__arch-mcp__search_aur,mcp__arch-mcp__diagnose_system,mcp__arch-mcp__query_package_history,mcp__arch-mcp__manage_orphans,mcp__arch-mcp__run_system_health_check
```

If the tools are absent, or a call returns an error, take the CLI fallback for that step and
record which path was used. Report the path taken for each check in the final summary so the
user can tell which evidence came from where.

## Step-to-tool map

| Step | arch-mcp | CLI fallback |
| --- | --- | --- |
| Arch news | `fetch_news(critical)`, `fetch_news(since_update)` | `curl https://archlinux.org/feeds/news/`, last upgrade from `/var/log/pacman.log` |
| Intervention research | `search_archwiki` | Read the news item's `link` and report it |
| Database staleness | `check_database_freshness` | `stat -c %y /var/lib/pacman/sync/*.db` |
| Official updates | `check_updates_dry_run` | `pacman -Qu` with a staleness caveat, then `yay -Syu --print` |
| AUR updates | none | `yay -Qua` |
| AUR metadata | `audit_package_security(metadata_risk)`, `search_aur` | AUR RPC query in [aur-review.md](aur-review.md) |
| Official replacement, typosquats | `get_official_package_info`, `search_aur` | `pacman -Si`, AUR RPC search |
| PKGBUILD patterns | `audit_package_security(pkgbuild_analysis)` | none; `scripts/scan-aur-recipe.sh` runs on both paths |
| Failed services | `diagnose_system(failed_services)` | `systemctl --failed` |
| Transaction errors | `query_package_history(failures)` | `grep -iE 'error|warning' /var/log/pacman.log` |
| Orphans | `manage_orphans(list)` | `pacman -Qdtq` |
| Health sweep | `run_system_health_check` | the individual commands above |

There is no AUR-upgrade equivalent in the server, so `yay -Qua` runs on both paths. It
queries the AUR over the network against installed versions and needs no root.

`fetch_news` applies `limit` to the number of news items it *scans*, not to the number of
critical items it returns, so a small limit silently hides older announcements. Pass at
least 30. Raising it further achieves nothing: the upstream feed holds only about ten items,
and `checked_items` in the response reports how many actually existed.

That feed length is a hard limit on what this gate can see. When the last full upgrade in
`/var/log/pacman.log` predates the oldest item in the feed, announcements from the
intervening period are unreachable. Report that gap rather than treating it as an absence of
news, and direct the user to the [Arch news archive](https://archlinux.org/news/) for the
uncovered window.

## Tools this skill does not use

Recorded so their absence is not mistaken for an oversight:

- `install_package_secure` — used for exactly one purpose: the `pacman-contrib` bootstrap in
  `SKILL.md`. It refuses AUR packages at any `confirm` value and cannot drive a full
  `yay -Syu` transaction, so it is never used for the upgrade itself. It runs
  `pacman -S --needed --noconfirm` with no `-y`, so it performs no database refresh.
  Without a graphical askpass helper it does not refuse; it warns and falls back to
  `sudo -n`, which succeeds only on a still-valid sudo timestamp and never prompts. Do not
  assume that timestamp exists: a failure there means no secure sudo method is available for
  this run, so take the deferred bootstrap route rather than retrying.
- `optimize_mirrors` — rewrites the mirrorlist. Out of scope for an upgrade.
- `manage_orphans(remove)`, `remove_packages` — this skill reports packages, never removes
  them.

## Trust posture

Server output is evidence, not a verdict.

- A clean `pkgbuild_analysis` never downgrades a `scripts/scan-aur-recipe.sh` finding, and a
  clean scanner run never downgrades an arch-mcp finding. Take the union of findings.
- Where the two disagree, adopt the higher risk level and explain the disagreement in the
  report.
- `pkgbuild_analysis` receives PKGBUILD text only. It cannot see `.install` scripts, patches,
  systemd units, vendored scripts, or committed binaries. Only the bundled scanner and manual
  inspection cover those, so both always run.
- The server runs locally on the machine being audited and is not an independent third party.
  It does not raise confidence the way a separate trust root would.
