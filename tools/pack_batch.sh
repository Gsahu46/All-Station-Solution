#!/usr/bin/env bash
# Pack one batch of 10 stations for the website: batches/batch-NN-stations-AAA-BBB.zip
#
#   tools/pack_batch.sh 1      # stations 001-010
#
# Refuses to pack unless all 10 stations pass tools/check_station.py. The zip holds, per station, the export
# contract from INTEGRATION.md (page.html, page-standalone.html, station.json, starter.zip, solutions.zip),
# plus an index.json for just this batch and a short README.
set -euo pipefail
[ $# -eq 1 ] || { sed -n '2,8p' "$0"; exit 1; }
ROOT=$(cd "$(dirname "$0")/.." && pwd); cd "$ROOT"
N=$1; FIRST=$(( (N - 1) * 10 + 1 )); LAST=$(( N * 10 ))
NAME=$(printf 'batch-%02d-stations-%03d-%03d' "$N" "$FIRST" "$LAST")
SLUGS=()
for id in $(seq "$FIRST" "$LAST"); do
  d=$(ls -d stations/"$(printf %03d "$id")"-* 2>/dev/null | head -1) || true
  [ -n "$d" ] || { echo "station $(printf %03d "$id") is not built yet" >&2; exit 2; }
  python3 tools/check_station.py "$d" >/dev/null || { python3 tools/check_station.py "$d"; exit 3; }
  SLUGS+=("$(basename "$d")")
done
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/$NAME/exports" batches
for s in "${SLUGS[@]}"; do cp -r "exports/$s" "$TMP/$NAME/exports/"; done
python3 - "$TMP/$NAME" "${SLUGS[@]}" <<'PY'
import json, pathlib, sys
out, slugs = pathlib.Path(sys.argv[1]), sys.argv[2:]
rows = [json.loads((pathlib.Path("exports") / s / "station.json").read_text()) for s in slugs]
keys = ("id", "slug", "title", "stage", "experience", "track", "types", "tests")
(out / "exports" / "index.json").write_text(json.dumps([{k: r[k] for k in keys} for r in rows], indent=1, ensure_ascii=False))
lines = [f"# {out.name}", "", "Stations in this batch (all pass tools/check_station.py):", "",
         "| Station | Title | Stage | Tests |", "|---|---|---|---|"]
lines += [f"| {r['id']:03d} | {r['title']} | {r['stage']} | {r['tests']['passed']}/{r['tests']['total']} |" for r in rows]
lines += ["", "Each `exports/NNN-slug/` folder follows the export contract in INTEGRATION.md:",
          "- `page.html`: the station page as body content (for hosts that add their own <html>/<head>)",
          "- `page-standalone.html`: the same page as a complete HTML document (open from disk, or any website)",
          "- `station.json`: the same content as data (header facts, levels -> tabs -> html, test counts)",
          "- `starter.zip`: the learner's Maven project, without solutions",
          "- `solutions.zip`: the challenge solutions (offer only after the learner has tried)",
          "", "`exports/index.json` lists only this batch. To integrate: copy `exports/*` into the website's stations folder",
          "and add each index.json entry to the site's station list (see INTEGRATION_MAP.md once it exists)."]
(out / "README.md").write_text("\n".join(lines) + "\n")
PY
rm -f "batches/$NAME.zip"
(cd "$TMP" && zip -qr "$ROOT/batches/$NAME.zip" "$NAME")
echo "batches/$NAME.zip ($(du -h "batches/$NAME.zip" | cut -f1)): ${#SLUGS[@]} stations"
