# First-Install AUR Review and Secure Sudo

Installing an AUR package for the first time is a decision to trust it, taken without the two
things an upgrade review can lean on: a prior recipe to diff against, and the user's earlier
decision to trust the package at all. The name itself is input chosen by whoever asked, and it
may not name what they think it names. Weight identity and provenance accordingly.

## Secure sudo selection

Use the first workable method:

1. **Attached interactive terminal:** run `yay` in a real PTY and let sudo read directly from
   the user. Do not read or relay the password through the agent.
2. **Graphical askpass:** require a graphical session and discover a helper without changing
   system configuration:

   ```bash
   command -v ksshaskpass || command -v ssh-askpass || command -v lxqt-openssh-askpass
   ```

   Invoke yay with the discovered absolute path, for example:

   ```bash
   env SUDO_ASKPASS=/usr/bin/ksshaskpass SUDO_ASKPASS_REQUIRE=force \
     yay --sudoflags -A -S PACKAGE
   ```

   Ask the user to interact only with the trusted graphical password dialog.
3. **No secure prompt available:** finish the read-only audit, then give the user the exact
   reviewed `yay` command to run in their own terminal. Never ask for a password in chat, pass
   it with `sudo -S`, store it, or create a permissive sudoers rule.

Do not assume `sudo -v` from a different PTY shares a timestamp; sudo commonly scopes
credentials by terminal.

## Resolve the requested name

The requested string is untrusted input. Never silently correct its spelling, and never pick a
package the user did not name.

1. **Already installed?** `pacman -Qi NAME`. Report the installed version and stop unless the
   user explicitly wants a rebuild or a different provider.
2. **Official repositories first.** Check `get_official_package_info` or `pacman -Si NAME`, and
   look for an official package that provides or replaces the name:

   ```bash
   pacman -Si NAME
   pacman -Ss "^NAME$"
   ```

   An official package is signed, reproducibly built by a trusted user, and needs none of this
   review. When one exists, install it from there and say so; do not audit an AUR alternative
   the user did not ask for.
3. **AUR lookup.** Query the RPC for an exact match, then for near matches:

   ```bash
   curl --fail --silent --show-error --get \
     --data-urlencode 'v=5' --data-urlencode 'type=info' \
     --data-urlencode 'arg[]=NAME' https://aur.archlinux.org/rpc/

   curl --fail --silent --show-error --get \
     --data-urlencode 'v=5' --data-urlencode 'type=search' --data-urlencode 'by=name' \
     --data-urlencode 'arg=NAME' https://aur.archlinux.org/rpc/
   ```

   Where [arch-mcp](arch-mcp.md) is available, `search_aur` covers the same ground with ranking
   and `audit_package_security(action='metadata_risk', package_name=NAME)` adds trust signals.
4. **Lookalike check.** Compare every candidate against the established packages around it.
   Treat as suspicious: a name one edit away from a popular package or from an official one; a
   base created recently that claims a long-standing project; near-zero votes for software with
   wide adoption; a maintainer with no other packages; a project URL whose domain does not match
   the software's known home. The ordinary AUR suffixes `-bin`, `-git`, `-beta` and `-nightly`
   are conventions, not red flags in themselves — the flag is a *lookalike competing with an
   established base*. Present the candidates with their evidence and let the user choose.
5. **Resolve `PackageBase`.** It differs from `pkgname` for split packages, and it is what the
   AUR Git repository is named. Everything downstream clones, audits, and re-checks the base.

## Collect package evidence

For the resolved package base, and for every AUR package in its dependency closure:

1. Record `PackageBase`, `Maintainer`, `Submitter`, `Version`, `FirstSubmitted`, `LastModified`,
   `OutOfDate`, `NumVotes`, `Popularity`, `URL`, `License`, `Depends`, `MakeDepends`,
   `CheckDepends` and `OptDepends`. There is no installed version to compare against; that is
   expected for a first install and is not itself a finding.
2. Clone the base into a fresh temporary directory and record the audited commit:

   ```bash
   directory=$(mktemp -d)
   git clone https://aur.archlinux.org/PACKAGE_BASE.git "$directory"
   git -C "$directory" rev-parse HEAD
   ```

3. Read the **whole** history, not a diff — there is no baseline to diff against. `git log
   --stat` shows who has touched the recipe, whether it changed hands, whether the history was
   recently squashed or rewritten, and whether the source URL has ever moved between domains.
4. Inspect every tracked file with `git ls-files`. A benign `PKGBUILD` does not make a malicious
   `.install`, patch, vendored script, desktop file, or systemd unit harmless.
5. Read the AUR comments for the package. Treat them as leads, not proof: they reveal
   unmaintained recipes, disputed ownership, and upstream moves that metadata does not show.

## Walk the AUR dependency closure

Installing a package installs everything it needs. Every AUR dependency executes its own build
code on this machine, so a review that stops at the requested package reviews almost nothing.

1. List what the recipe declares, without executing it:

   ```bash
   scripts/list-recipe-deps.sh /path/to/clone
   ```

   It reads `.SRCINFO` only and prints `TYPE<TAB>NAME` lines for `depends`, `makedepends`,
   `checkdepends` and `optdepends`. Exit `0` succeeded, `64` usage error, `66` no readable
   `.SRCINFO`. On `66`, do not fall back to sourcing the `PKGBUILD`; report that the recipe ships
   no `.SRCINFO` — itself unusual and worth noting — and read the arrays by eye instead.
2. Classify each name with `get_official_package_info` or `pacman -Si`. Official dependencies
   need no audit. Anything that resolves only in the AUR does.
3. Audit every AUR `depends`, `makedepends` and `checkdepends` through this same procedure.
   `makedepends` are not a lesser category: they run at build time with the user's privileges.
4. Keep a set of visited package bases so cycles and diamonds terminate. Record the closure and
   the audited commit for each member.
5. `optdepends` are not installed by default. Record them and their purpose; audit one only if
   the user asks for it.
6. A closure too large or too deep to review honestly is itself a finding. Stop, report its size
   and shape, and let the user decide — never let it decay into skimming.

## Static review before execution

Do not source a `PKGBUILD`, run `makepkg`, or invoke its functions until this review is
complete; shell code at top level can execute during parsing.

Check:

- **Identity:** package and upstream names are not typosquats; project URL and source domains
  belong to the expected upstream or a documented release host.
- **Purpose:** the build does what a package of this kind should do, and nothing else. With no
  prior version to compare against, "unexplained" is the operative word — anything the package's
  stated purpose does not account for needs an explanation before it is accepted.
- **Source immutability:** prefer versioned release artifacts or commit hashes over branches,
  tags that can move, VCS HEAD, "latest" URLs, or generated download endpoints.
- **Integrity:** require strong non-`SKIP` hashes for artifacts. Prefer upstream signatures with
  appropriate `validpgpkeys`. A matching hash proves consistency with the recipe, not that the
  maintainer selected a benign artifact.
- **Build behavior:** investigate network downloads outside `source=()`, `curl | sh`, `eval`,
  encoded payloads, credential access, privilege commands, device access, writes outside build
  roots, or unexpected telemetry.
- **Binary provenance:** investigate prebuilt executables, AppImages, distribution packages,
  bundled toolchains, and binaries committed directly to the AUR repository.
- **Lifecycle code:** inspect `.install` hooks, systemd units, tmpfiles, sysusers, udev rules,
  cron jobs, shell profiles, and package scripts for persistence or privilege changes.
- **Ownership/context:** note orphaned or newly adopted packages, unexpected uploader identity,
  abrupt rewrites, deleted history, low-use lookalikes, and unexplained source-domain changes.

Where [arch-mcp](arch-mcp.md) is available, run
`audit_package_security(action='pkgbuild_analysis')` as a second opinion, passing the
`PKGBUILD` read from the disposable clone at the audited commit. It receives PKGBUILD text
only and cannot see `.install` scripts, patches, systemd units, vendored scripts, or
committed binaries, so it supplements `scripts/scan-aur-recipe.sh` and manual inspection
rather than replacing either. Take the union of all findings, and where the sources disagree
adopt the higher risk level and explain the disagreement.

After the static review, `makepkg --verifysource` may be run in the disposable clone. Stop if
fetching or verification fails. Do not replace failed hashes, add `SKIP`, or import signing keys
merely to make verification pass.

## First-install risk decision

Classify the complete evidence, not just scanner output. The verdict for the transaction is the
highest verdict in the closure: a low-risk package with a medium-risk AUR dependency is a
medium-risk install.

- **Low:** exact name match with no competing lookalike; upstream URL and source domains that
  belong to the project the package claims to be; an actively maintained base that is not
  orphaned or flagged out of date; adoption or a long, coherent history consistent with the
  software's reputation; immutable HTTPS sources with strong non-`SKIP` hashes or upstream
  signatures; a build that matches normal practice for its language and toolchain; no privileged,
  persistence, credential, or unexplained network behaviour; every AUR dependency also low.
- **Medium:** orphaned or newly adopted; a very new base, or a maintainer with no track record;
  near-zero adoption for software claiming wide use; mutable VCS source or `pkgver()`; `SKIP`;
  prebuilt binaries with plausible but unverifiable provenance; install hooks, systemd units,
  sysusers, tmpfiles or udev rules; a source domain that is merely undocumented rather than
  wrong; any AUR dependency at medium. Stop and request approval with the evidence and safer
  alternatives, including any official-repository or Flatpak equivalent.
- **High:** hash or signature mismatch, obfuscated or remotely piped execution, credential
  harvesting, unexplained privilege escalation or persistence, a name that is a lookalike of an
  established package, a source domain inconsistent with the stated upstream, or any behaviour
  inconsistent with the package's purpose; any AUR dependency at high. Recommend rejection and
  require an explicit package-specific override.

Two failure modes to guard against, both specific to a first install:

- **The missing baseline is not evidence.** Every first install lacks a prior recipe. Do not
  grade that as a medium finding, or the gate stops discriminating. Compensate by weighting
  identity, provenance, and history more heavily instead.
- **Adoption is not safety.** Votes and popularity measure how many people installed it, which
  is exactly what a compromised popular package also has. They raise confidence that the name is
  the right one, not that the code is benign.

The absence of findings, from the bundled scanner or from arch-mcp, is not a low-risk verdict.
Both are pattern matchers running on the same machine as the audit, and neither is an
independent trust root. Conversely, common VCS packaging can trigger medium indicators without
being malicious; explain why it is necessary and what remains mutable.

## Prevent review/install races

Immediately before starting yay, compare each audited commit with the current remote:

```bash
git ls-remote https://aur.archlinux.org/PACKAGE_BASE.git refs/heads/master
```

Abort if any changed. During yay's interactive diff/build review, confirm the fetched AUR
checkouts still correspond to the audited commits, and watch for a package base that was never
in the audited closure: dependency resolution can introduce one that appeared after the review.
Audit any such package before allowing the transaction to proceed. If the tool cannot expose a
trustworthy checkpoint before executing package code, stop and have the user run the reviewed
transaction interactively rather than silently accepting it.
