#!/usr/bin/env bash
# Iterative development walkthrough: generate the interface, add the
# hand-written model, rename a port, regenerate in place, and watch the build
# refuse at the exact line that still names the old port.
#
# Needs the `pyfmi-sysml` console script and OpenModelica. Override with
#   PYFMI=/path/to/pyfmi-sysml OMC=/path/to/omc ./run.sh
set -euo pipefail

PYFMI=${PYFMI:-pyfmi-sysml}
OMC=${OMC:-omc}
here=$(cd "$(dirname "$0")" && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

package=GeneratedInterfaces
component=Scaler
out=$work/build

command -v "$PYFMI" >/dev/null || { echo "missing $PYFMI" >&2; exit 2; }
command -v "$OMC" >/dev/null || { echo "missing $OMC" >&2; exit 2; }

fail() {
  printf 'FAIL %s\n%s\n' "$1" "$2" >&2
  exit 1
}

generate() {
  "$PYFMI" modelica "$1" -o "$out" >/dev/null
}

build() {
  printf 'loadFile("%s/%s/package.mo");\nbuildModel(%s.%s);\ngetErrorString();\n' \
    "$out" "$package" "$package" "$component" > "$out/build.mos"
  (cd "$out" && "$OMC" build.mos 2>&1 || true)
}

expect_built() {
  local label=$1 text=$2
  grep -q "Error" <<<"$text" && fail "$label" "$text"
  [[ -f "$out/$package.$component" ]] || fail "$label" "$text"
  printf 'PASS %s\n' "$label"
}

expect_text() {
  local label=$1 text=$2 pattern=$3
  grep -qF "$pattern" <<<"$text" || fail "$label" "$text"
  printf 'PASS %s\n      %s\n' "$label" "$(grep -m1 -F "$pattern" <<<"$text" | sed 's/^ *//')"
}

echo "== 1. first use: generate the interface, then add the model logic"
generate "$here/v1.sysml"
cp "$here/logic.mo" "$out/$package/$component.mo"
expect_built "revision 1 builds" "$(build)"

echo "== 2. the architecture renames the input port raw -> command; regenerate"
before=$(cksum "$out/$package/$component.mo")
generate "$here/v2.sysml"
after=$(cksum "$out/$package/$component.mo")
[[ "$before" == "$after" ]] || fail "regeneration rewrote the model" ""
printf 'PASS regeneration left %s.mo untouched\n' "$component"
text=$(build)
expect_text "revision 2 fails at the port change" "$text" "not found in scope"

echo "== 3. the fix is local to the hand-written file"
sed -i 's/raw\.value/command\.value/g' "$out/$package/$component.mo"
expect_built "revision 2 builds after the rename" "$(build)"

echo "== 4. the output port gains a clipped field; regenerate"
generate "$here/v3.sysml"
text=$(build)
expect_text "revision 3 fails on an unbalanced member" "$text" "Too few equations"
expect_text "the new member is named" "$text" "limited.clipped"

echo "== done: the interface moved, the model stayed, the build said exactly where"
