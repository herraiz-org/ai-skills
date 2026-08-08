# AUR Review and Secure Sudo

## Secure sudo selection

Use the first workable method:

1. **Attached interactive terminal:** run `yay` in a real PTY and let sudo read directly from the user. Do not read or relay the password through the agent.
2. **Graphical askpass:** require a graphical session and discover a helper without changing system configuration:

   ```bash
   command -v ksshaskpass || command -v ssh-askpass || command -v lxqt-openssh-askpass
   ```

   Invoke yay with the discovered absolute path, for example:

   ```bash
   env SUDO_ASKPASS=/usr/bin/ksshaskpass SUDO_ASKPASS_REQUIRE=force \
     yay --sudoflags -A -Syu --print
   ```

   Use the same environment for the final `yay -Syu`. Ask the user to interact only with the trusted graphical password dialog.
3. **No secure prompt available:** finish the read-only audit, then give the user the exact reviewed `yay` command to run in their own terminal. Never ask for a password in chat, pass it with `sudo -S`, store it, or create a permissive sudoers rule.

Do not assume `sudo -v` from a different PTY shares a timestamp; sudo commonly scopes credentials by terminal.

## Collect package evidence

For each name returned by `yay -Qua`:

1. Query current metadata without executing package code. Where [arch-mcp](arch-mcp.md) is
   available, prefer `audit_package_security(action='metadata_risk', package_name=PACKAGE)`
   for trust signals and `search_aur` for lookalike and typosquat comparison. Otherwise, or
   whenever exact fields are needed, use the AUR RPC directly:

   ```bash
   curl --fail --silent --show-error --get \
     --data-urlencode 'v=5' --data-urlencode 'type=info' \
     --data-urlencode 'arg[]=PACKAGE' https://aur.archlinux.org/rpc/
   ```

2. Record `PackageBase`, maintainer, version, first/last modified time, out-of-date state, votes, popularity, URL, dependencies, and the installed version from `pacman -Q PACKAGE`. Check with `get_official_package_info` or `pacman -Si PACKAGE` whether an official package now supersedes the AUR one, and report that migration as a safer alternative.
3. Clone the package base into a temporary directory and record `git rev-parse HEAD`, `git log --stat`, and relevant recipe diffs. Prefer a cached prior recipe only when its commit and relationship to the installed version are clear. If the installed recipe cannot be established, mark the baseline as uncertain.
4. Inspect every tracked file with `git ls-files`. A benign `PKGBUILD` does not make a malicious `.install`, patch, vendored script, desktop file, or systemd unit harmless.
5. Check AUR package comments when metadata, ownership, sudden rewrites, or upstream provenance are unclear. Treat comments as leads, not proof.

## Static review before execution

Do not source a `PKGBUILD`, run `makepkg`, or invoke its functions until this review is complete; shell code at top level can execute during parsing.

Check:

- **Identity:** package and upstream names are not typosquats; project URL and source domains belong to the expected upstream or a documented release host.
- **Change scope:** version, dependencies, sources, build steps, install hooks, services, permissions, and filesystem destinations match the stated update.
- **Source immutability:** prefer versioned release artifacts or commit hashes over branches, tags that can move, VCS HEAD, “latest” URLs, or generated download endpoints.
- **Integrity:** require strong non-`SKIP` hashes for artifacts. Prefer upstream signatures with appropriate `validpgpkeys`. A matching hash proves consistency with the recipe, not that the maintainer selected a benign artifact.
- **Build behavior:** investigate network downloads outside `source=()`, `curl | sh`, `eval`, encoded payloads, credential access, privilege commands, device access, writes outside build roots, or unexpected telemetry.
- **Binary provenance:** investigate prebuilt executables, AppImages, distribution packages, bundled toolchains, and binaries committed directly to the AUR repository.
- **Lifecycle code:** inspect `.install` hooks, systemd units, tmpfiles, sysusers, udev rules, cron jobs, shell profiles, and package scripts for persistence or privilege changes.
- **Ownership/context:** note orphaned or newly adopted packages, unexpected uploader identity, abrupt rewrites, deleted history, low-use lookalikes, and unexplained source-domain changes.

Where [arch-mcp](arch-mcp.md) is available, run
`audit_package_security(action='pkgbuild_analysis')` as a second opinion, passing the
`PKGBUILD` read from the disposable clone at the audited commit. It receives PKGBUILD text
only and cannot see `.install` scripts, patches, systemd units, vendored scripts, or
committed binaries, so it supplements `scripts/scan-aur-recipe.sh` and manual inspection
rather than replacing either. Take the union of all findings, and where the sources disagree
adopt the higher risk level and explain the disagreement.

After the static review, `makepkg --verifysource` may be run in the disposable clone. Stop if fetching or verification fails. Do not replace failed hashes, add `SKIP`, or import signing keys merely to make verification pass.

## Risk decision

Classify the complete evidence, not just scanner output:

- **Low:** transparent expected change; maintained package; recognized upstream; immutable HTTPS sources; valid strong hashes or signatures; no unexplained dependency, hook, privilege, binary, or domain changes; audited commit matches the candidate to build.
- **Medium:** missing historical baseline; mutable VCS source; `SKIP`; new source domain, dependency, binary, hook, service, or substantial build rewrite; unclear maintainer/provenance; verification that is incomplete but not demonstrably malicious. Stop and request approval with the evidence and safer alternatives.
- **High:** hash/signature mismatch, obfuscated or remotely piped execution, credential harvesting, unexplained privilege escalation or persistence, typosquatting, a compromised-looking upstream/source swap, or other behavior inconsistent with package purpose. Recommend rejection and require an explicit package-specific override.

The absence of findings, from the bundled scanner or from arch-mcp, is not a low-risk verdict. Both are pattern matchers running on the same machine as the audit, and neither is an independent trust root. Conversely, common VCS packaging can trigger medium indicators without being malicious; explain why it is necessary and what remains mutable.

## Prevent review/install races

Immediately before starting yay, compare the audited commit with:

```bash
git ls-remote https://aur.archlinux.org/PACKAGE_BASE.git refs/heads/master
```

Abort if it changed. During yay's interactive diff/build review, confirm the fetched AUR checkout and displayed changes still correspond to the audited commit. If the tool cannot expose a trustworthy checkpoint before executing package code, stop and have the user run the reviewed transaction interactively rather than silently accepting it.

