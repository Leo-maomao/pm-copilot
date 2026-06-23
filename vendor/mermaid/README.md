# Mermaid Runtime

This directory vendors the browser runtime used by `scripts/render_prd_html.py` when a PRD contains Mermaid flow diagrams.

- Package: `mermaid`
- Version: `11.13.0`
- File copied into PRD output: `mermaid.min.js`
- License: MIT, preserved in `LICENSE`

The renderer copies this file to `<run-folder>/assets/mermaid.min.js` so `prd.html` can render flowcharts offline without CDN access.
