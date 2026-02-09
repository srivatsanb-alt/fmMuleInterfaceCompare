#!/bin/bash
set -eo pipefail
# Generate dependency graphs for the `mule` submodule using pyreverse (pylint)
# Outputs `classes_mule.png` and `packages_mule.png` to docs/dep_graphs

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TARGET_PATH="$ROOT_DIR/mule"
OUT_DIR="$ROOT_DIR/docs/dep_graphs"

mkdir -p "$OUT_DIR"

if ! command -v pyreverse >/dev/null 2>&1; then
  echo "✗ pyreverse not found. Install pylint: pip install pylint"
  exit 1
fi

echo "Running pyreverse on: $TARGET_PATH"
export PYTHONPATH="$ROOT_DIR":${PYTHONPATH:-}

pushd "$ROOT_DIR" >/dev/null

# Run pyreverse on the mule directory, capturing output to handle errors
# -A: ignore __init__.py and __pycache__; -S: with nested modules as inner classes
echo "Analyzing Python files (this may take a moment)..."
if pyreverse -o png -p mule -A "$TARGET_PATH" -d "$OUT_DIR" 2>&1 | grep -v "^Parsing Python code failed" | grep -v "^Failed to import"; then
  :
fi

echo ""

# Check if files were generated in cwd or in OUT_DIR
popd >/dev/null

# Look for generated files in cwd and output dir
for f in "$ROOT_DIR"/classes_mule.png "$ROOT_DIR"/packages_mule.png "$OUT_DIR"/classes_mule.png "$OUT_DIR"/packages_mule.png; do
  if [ -f "$f" ]; then
    basename_f=$(basename "$f")
    if [[ "$f" != *"$OUT_DIR"* ]]; then
      mv "$f" "$OUT_DIR/" 2>/dev/null || true
    fi
    echo "✓ $(basename "$basename_f") size: $(stat -f%z "$OUT_DIR/$basename_f" 2>/dev/null || stat -c%s "$OUT_DIR/$basename_f" 2>/dev/null || echo 'unknown') bytes"
  fi
done

# Report final status
if ls "$OUT_DIR"/*.png >/dev/null 2>&1; then
  echo ""
  echo "✓ Dependency graphs saved to: $OUT_DIR"
  ls -lh "$OUT_DIR"/*.png
else
  echo ""
  echo "⚠ No PNG files generated. Common causes:"
  echo "  - Graphviz 'dot' command not installed (brew install graphviz)"
  echo "  - Python syntax errors in mule codebase"
  echo "  - Run with -v for verbose output: pyreverse -v -o png -p mule -A mule"
fi
