#!/usr/bin/env bash
# Rebuilds the entire project from scratch: data -> analysis -> charts -> reports.
# Everything is seeded, so this is deterministic.
set -euo pipefail
cd "$(dirname "$0")"

echo "==> 1/5  generating data"
python3 src/generate_data.py

echo "==> 2/5  running analyses + charts"
python3 src/run_analysis.py

echo "==> 3/5  rendering README + executive summary"
python3 src/make_report.py

echo "==> 4/5  building the notebook"
python3 src/build_notebook.py

echo "==> 5/5  weekly monitor"
python3 src/monitor.py || echo "   (monitor exited non-zero: a metric is RED)"

echo
echo "done. open README.md, or run:  streamlit run dashboard/app.py"
