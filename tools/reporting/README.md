# Reproducible reporting

Use an isolated Python environment with `requirements.txt` for measured charts. `render-results.py` consumes only result JSON, leaves missing series unavailable, and writes SVG plus PNG. No synthetic fallback data is used. Single short samples are not confidence intervals or production benchmarks.

`render-architecture.sh` renders every `docs/diagrams/*.mmd` to `docs/images/architecture/*.svg` and high-resolution `*.png` (1600-pixel viewport, scale 2). The Phase 5 run used `@mermaid-js/mermaid-cli@11.12.0` and the installed Google Chrome. Set `MERMAID_CLI` to its executable. Optional `PUPPETEER_CONFIG` and `MERMAID_CONFIG` point to reviewed local JSON files; browser setup is external to this repository. Never feed untrusted browser launch arguments into a shared CI runner.

## Final package

From the repository root:

```sh
python3 -m venv /tmp/dbaas-reporting
/tmp/dbaas-reporting/bin/pip install -r tools/reporting/requirements.txt
MPLCONFIGDIR=/tmp/dbaas-mpl /tmp/dbaas-reporting/bin/python tools/reporting/final-measurements.py
MERMAID_CLI=/path/to/mmdc bash tools/reporting/render-architecture.sh
python3 tools/reporting/check-links.py
```

`final-measurements.py` reads the preserved continuation artifacts and writes the canonical performance report, eight SVG/PNG chart pairs and `results/validation/phase6/measured-summary.json`. It does not run benchmarks or change historical measurements. `docs/images/results/final/manifest.json` maps charts to their sources. Older generators target historical packages; use the final generator for the current report.
