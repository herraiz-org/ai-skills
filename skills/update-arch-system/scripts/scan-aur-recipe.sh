#!/usr/bin/env bash
set -uo pipefail

if (( $# == 0 )); then
  echo "usage: ${0##*/} PACKAGE_DIRECTORY [...]" >&2
  exit 64
fi

high=0
medium=0

emit_matches() {
  local level=$1 message=$2 pattern=$3 file=$4 matches
  matches=$(grep -EnI -- "$pattern" "$file" 2>/dev/null) || return 0
  while IFS= read -r match; do
    [[ -n $match ]] || continue
    printf '%s\t%s:%s\t%s\n' "$level" "$file" "$match" "$message"
    if [[ $level == HIGH ]]; then
      high=1
    else
      medium=1
    fi
  done <<< "$matches"
}

for directory in "$@"; do
  if [[ ! -d $directory ]]; then
    printf 'ERROR\t%s\tnot a directory\n' "$directory" >&2
    high=1
    continue
  fi

  while IFS= read -r -d '' file; do
    emit_matches HIGH 'remote content piped to an interpreter' \
      '(curl|wget)[^|;&]*(\||[[:space:]])[^#]*(sh|bash|zsh|python|perl|ruby)([[:space:];&]|$)' "$file"
    emit_matches HIGH 'privilege command in package-controlled code' \
      '(^|[;&|[:space:]])(sudo|doas|su)([[:space:]]|$)' "$file"
    emit_matches HIGH 'possible access to credentials or secret stores' \
      '(\.ssh|\.gnupg|\.aws|\.kube|netrc|id_rsa|id_ed25519|credentials|api[_-]?key|auth[_-]?token)' "$file"
    emit_matches HIGH 'dynamic or encoded command execution' \
      '(^|[;&|[:space:]])eval([[:space:]]|$)|base64[[:space:]]+(-d|--decode)[^|;&]*(\||>)' "$file"

    emit_matches MEDIUM 'integrity check explicitly skipped' \
      "(sha(1|224|256|384|512)sums|md5sums|b2sums)[^#]*SKIP" "$file"
    emit_matches MEDIUM 'weak hash algorithm cannot establish source integrity' \
      '(md5sums|sha1sums)[^#]*=[^#]*[0-9a-fA-F]{32}' "$file"
    emit_matches MEDIUM 'unencrypted source URL' \
      "(^|[[:space:]'\"])(source[^=]*=|[a-zA-Z0-9_]+=)?[^#]*http://" "$file"
    emit_matches MEDIUM 'mutable VCS source or pkgver function' \
      "(git\+|hg\+|svn\+|bzr\+|^pkgver[[:space:]]*\(\))" "$file"
    emit_matches MEDIUM 'network retrieval outside normal source verification needs review' \
      '(^|[;&|[:space:]])(curl|wget|aria2c|fetch)([[:space:]]|$)' "$file"
    emit_matches MEDIUM 'prebuilt package or executable artifact needs provenance review' \
      '\.(AppImage|deb|rpm|exe|msi)([?"'"'"'[:space:]]|$)' "$file"
    emit_matches MEDIUM 'package lifecycle or persistence mechanism needs review' \
      '(systemctl|udev|tmpfiles|sysusers|cron|\.install([[:space:]"'"'"']|$))' "$file"
  done < <(find "$directory" -type f ! -path '*/.git/*' -print0)
done

if (( high )); then
  exit 2
fi
if (( medium )); then
  exit 1
fi
exit 0
