#!/usr/bin/env bash
set -uo pipefail

# List the dependencies declared by an AUR recipe, by reading .SRCINFO only.
#
# A PKGBUILD cannot be parsed without executing it: it is a shell script, and
# top-level code runs the moment it is sourced. .SRCINFO is the generated,
# inert, key/value rendering of the same arrays, so it is the only build input
# safe to read before the recipe has been reviewed.
#
# Output: one "TYPE<TAB>NAME" line per dependency, sorted and deduplicated,
# with version constraints, optdepends descriptions, and architecture suffixes
# removed. Exit 0 on success (empty output means no dependencies), 64 on a
# usage error, 66 when no readable .SRCINFO exists.

if (( $# != 1 )); then
  echo "usage: ${0##*/} PACKAGE_DIRECTORY" >&2
  exit 64
fi

directory=$1
srcinfo="$directory/.SRCINFO"

if [[ ! -f $srcinfo || ! -r $srcinfo ]]; then
  printf 'ERROR\t%s\tno readable .SRCINFO\n' "$directory" >&2
  exit 66
fi

trim() {
  local text=$1
  text=${text#"${text%%[![:space:]]*}"}
  text=${text%"${text##*[![:space:]]}"}
  printf '%s' "$text"
}

{
  while IFS= read -r line || [[ -n $line ]]; do
    [[ $line == *=* ]] || continue

    # Keys never contain '=' or whitespace, so the first '=' splits the line and
    # the value keeps any '=' of its own version constraint.
    key=${line%%=*}
    key=${key//[[:space:]]/}
    value=$(trim "${line#*=}")

    case $key in
      depends|depends_*) type=depends ;;
      makedepends|makedepends_*) type=makedepends ;;
      checkdepends|checkdepends_*) type=checkdepends ;;
      optdepends|optdepends_*) type=optdepends ;;
      *) continue ;;
    esac

    # optdepends carry a free-text description after the first colon; drop it
    # before the version constraint, which sits on the name side.
    name=$(trim "${value%%:*}")
    name=${name%%[<>=]*}
    [[ -n $name ]] || continue

    printf '%s\t%s\n' "$type" "$name"
  done < "$srcinfo"
} | sort -u

exit 0
