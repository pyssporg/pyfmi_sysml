#!/usr/bin/env bash
# Self-checking walkthrough of the Simulink generation seam.
#
#   1. generate bus types + manifest from the fixture
#   2. build the hand model and simulate it (expect y.value == 6)
#   3. check the model's interface against the manifest (expect a match)
#   4. regenerate from a port-renamed copy and require the checker to fail
#
# MATLAB runs with build/ as its working directory, so every cache and codegen
# artifact Simulink drops stays inside the one ignored folder.
set -euo pipefail

MATLAB=${MATLAB:-/opt/MATLAB/R2023b/bin/matlab}
# The caller (the pytest wrapper) passes the invoking interpreter so the
# walkthrough sees the same environment as the suite.
PYTHON=${PYTHON:-python3}

here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
build="$here/build"
cd "$here"

fixture=$(cd ../fixtures/minimal && pwd)/minimal.sysml
rm -rf "$build"
mkdir -p "$build"

run_matlab() {
    "$MATLAB" -batch "cd('$build'); addpath('$build'); addpath('$here'); $1"
}

"$PYTHON" generate_types.py "$fixture" "$build"
echo "ok generate"

# One MATLAB process per stage: stages share files, not workspace state.
run_matlab "defineBusTypes; hand_model; simulate_model"
echo "ok simulate"

run_matlab "defineBusTypes; check_interface"
echo "ok interface"

mkdir -p "$build/drift"
"$PYTHON" generate_types.py v2.sysml "$build/drift" >/dev/null
drift_log="$build/drift.log"
export PORTS_JSON="$build/drift/ports.json"
if run_matlab "defineBusTypes; check_interface" >"$drift_log" 2>&1; then
    echo "FAIL: the renamed port was not detected" >&2
    exit 1
fi
unset PORTS_JSON
if ! grep -q "model 'u'" "$drift_log" || ! grep -q "manifest 'command'" "$drift_log"; then
    echo "FAIL: drift message did not name both ports" >&2
    cat "$drift_log" >&2
    exit 1
fi
echo "ok drift detected"
