#!/usr/bin/env bash
# Build one station end to end, so every number and example on its page comes from a real run.
#
#   tools/build_station.sh stations/NNN-slug [--capture]
#
#  1. Runs the station's tests                  -> docs/test-run.txt       (must pass, or the build stops)
#  2. Runs them against review/*.java            -> docs/review-run.txt     (expected to fail; skipped if no review/)
#  3. Runs station + challenge tests with
#     challenge/solution/* copied in             -> docs/challenge-run.txt  (must pass; skipped if no challenge/)
#  4. --capture: starts compose + the app and runs docs/capture.sh -> docs/captures/*.txt
#  5. Renders exports/<slug>/page.html and station.json, and the station's README.md
#  6. Packs exports/<slug>/starter.zip (no solutions) and solutions.zip, and updates exports/index.json
#
# Needs: JDK 25 (or set JAVA_VERSION=21), Docker running, python3, pandoc, zip.
set -euo pipefail

[ $# -ge 1 ] || { sed -n '2,15p' "$0"; exit 1; }
ROOT=$(cd "$(dirname "$0")/.." && pwd)
DIR=$(cd "$1" && pwd)
NAME=$(basename "$DIR")
CAPTURE=${2:-}
OUT="$ROOT/exports/$NAME"
LOG=$(mktemp)
# Full Maven output goes to $LOG (shown when something fails); the saved run keeps only the result lines.
mvn_test() { ./mvnw -B ${JAVA_VERSION:+-Djava.version=$JAVA_VERSION} test > "$LOG" 2>&1 || true
             grep -E "Tests run:|BUILD" "$LOG" | sed -E 's/, Time elapsed: [0-9.]+ s//; s/ <<< FAILURE!//'; }
show_log() { echo "--- last lines of the Maven output:" >&2; grep -E "ERROR|FAIL|Caused by|release version" "$LOG" | head -20 >&2; }
pkg_dir() { sed -n 's/^package \([a-z0-9_.]*\);.*/\1/p' "$1" | head -1 | tr . /; }
copy_project() { local to=$1; mkdir -p "$to"; cp -r pom.xml mvnw mvnw.cmd .mvn src "$to"/; }

if grep -q testcontainers "$DIR/pom.xml" || [ -f "$DIR/compose.yaml" ]; then
  docker info >/dev/null 2>&1 || { echo "Docker is not running. This station's tests and app use containers; start Docker and run again." >&2; exit 2; }
fi
cd "$DIR"
mkdir -p docs

echo "1/6 station tests"
mvn_test > docs/test-run.txt || true
grep -q "BUILD SUCCESS" docs/test-run.txt || { show_log; echo "Station tests failed. Fix them before building the page." >&2; exit 3; }
tail -2 docs/test-run.txt

TMP=$(mktemp -d); trap 'rm -rf "$TMP" "$LOG"; [ -n "${APP_PID:-}" ] && kill "$APP_PID" 2>/dev/null; [ -n "${COMPOSE_UP:-}" ] && docker compose -f "$DIR/compose.yaml" down -v >/dev/null 2>&1; true' EXIT

if compgen -G "review/*.java" >/dev/null; then
  echo "2/6 flawed version (failures expected)"
  copy_project "$TMP/review"
  for f in review/*.java; do cp "$f" "$TMP/review/src/main/java/$(pkg_dir "$f")/"; done
  (cd "$TMP/review" && mvn_test) > docs/review-run.txt || true
  grep -q "Tests run:" docs/review-run.txt || { show_log; echo "The flawed version did not compile or run; fix review/." >&2; exit 4; }
  tail -2 docs/review-run.txt
fi

if compgen -G "challenge/*Test.java" >/dev/null; then
  echo "3/6 challenge tests against the solutions"
  copy_project "$TMP/solved"
  for f in challenge/solution/*.java; do cp "$f" "$TMP/solved/src/main/java/$(pkg_dir "$f")/"; done
  for f in challenge/*Test.java; do cp "$f" "$TMP/solved/src/test/java/$(pkg_dir "$f")/"; done
  if [ -f challenge/solution/pom-additions.xml ]; then
    python3 - "$TMP/solved/pom.xml" challenge/solution/pom-additions.xml <<'PY'
import re, sys
pom, add = open(sys.argv[1]).read(), open(sys.argv[2]).read()
add = re.sub(r"<!--.*?-->", "", add, flags=re.S).strip()
i = pom.index("</dependencies>")
open(sys.argv[1], "w").write(pom[:i] + add + "\n    " + pom[i:])
PY
  fi
  (cd "$TMP/solved" && mvn_test) > docs/challenge-run.txt || true
  grep -q "BUILD SUCCESS" docs/challenge-run.txt || { show_log; echo "A challenge test fails against its solution." >&2; exit 5; }
  tail -2 docs/challenge-run.txt
fi

if [ "$CAPTURE" = "--capture" ]; then
  echo "4/6 capturing real requests"
  [ -x docs/capture.sh ] || { echo "docs/capture.sh is missing or not executable." >&2; exit 6; }
  if [ -f compose.yaml ]; then
    docker compose up -d --wait >/dev/null; COMPOSE_UP=1   # services need a healthcheck in compose.yaml for --wait to mean "ready"
  fi
  ./mvnw -B -q ${JAVA_VERSION:+-Djava.version=$JAVA_VERSION} -DskipTests package
  java -jar target/*.jar > "$TMP/app.log" 2>&1 & APP_PID=$!
  for _ in $(seq 1 90); do curl -s -o /dev/null http://localhost:8080/ && break; sleep 1; done
  docs/capture.sh
  kill "$APP_PID"; APP_PID=""
  if [ -n "${COMPOSE_UP:-}" ]; then docker compose down -v >/dev/null 2>&1 || true; COMPOSE_UP=""; fi
fi

echo "5/6 rendering"
python3 "$ROOT/curriculum/station_render.py" "$DIR" "$OUT"

echo "6/6 packing"
rm -rf target
rm -f "$OUT/starter.zip" "$OUT/solutions.zip"
(cd .. && zip -qr "$OUT/starter.zip" "$NAME" -x "$NAME/challenge/solution/*" "$NAME/target/*" "*.DS_Store" "$NAME/docs/page.py")
[ -d challenge/solution ] && (cd .. && zip -qr "$OUT/solutions.zip" "$NAME/challenge/solution")
python3 - "$ROOT/exports" <<'PY'
import json, pathlib, sys
root = pathlib.Path(sys.argv[1])
rows = []
for f in sorted(root.glob("*/station.json")):
    d = json.loads(f.read_text())
    rows.append({k: d[k] for k in ("id", "slug", "title", "stage", "experience", "track", "types", "tests")})
(root / "index.json").write_text(json.dumps(sorted(rows, key=lambda r: r["id"]), indent=1, ensure_ascii=False))
print(f"exports/index.json: {len(rows)} station(s)")
PY
echo "done: $OUT"
