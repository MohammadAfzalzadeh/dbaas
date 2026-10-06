#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
command -v mmdc >/dev/null || { echo 'Install a reviewed Mermaid CLI (mmdc) and browser to render repository diagrams.' >&2; exit 1; }
mkdir -p docs/images
for source in docs/diagrams/*.mmd; do
  mmdc -i "$source" -o "docs/images/$(basename "${source%.mmd}").svg"
done
