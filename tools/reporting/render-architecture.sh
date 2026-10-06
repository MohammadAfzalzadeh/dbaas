#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.."
: "${MERMAID_CLI:=mmdc}"
output=docs/images/architecture
mkdir -p "$output"
args=()
if [[ -n ${PUPPETEER_CONFIG:-} ]]; then args+=(-p "$PUPPETEER_CONFIG"); fi
if [[ -n ${MERMAID_CONFIG:-} ]]; then args+=(-c "$MERMAID_CONFIG"); fi
for source in docs/diagrams/*.mmd; do
  stem=$(basename "${source%.mmd}")
  "$MERMAID_CLI" -i "$source" -o "$output/$stem.svg" -b white "${args[@]}"
  "$MERMAID_CLI" -i "$source" -o "$output/$stem.png" -b white -w 1600 -s 2 "${args[@]}"
done
