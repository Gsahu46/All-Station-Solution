"""Gate for one built station: does it meet STATION_STANDARD.md? Prints every problem, exits 1 if any.

    python3 tools/check_station.py stations/NNN-slug

Run it after tools/build_station.sh. A station is not done until this prints "OK".
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ROADMAP = {s["id"]: s for s in json.loads((ROOT / "curriculum" / "roadmap.json").read_text())["stations"]}
TAB_IDS = ["understand", "spec", "api", "trap", "code", "tests", "practice", "design", "production", "interview", "review"]
# Each station type needs a test class whose name contains one of these words (STATION_STANDARD "Required tests by station type").
TYPE_TESTS = {"Database": ["Database"], "Security": ["Security", "Auth"], "Concurrency": ["Concurrency"],
              "Messaging": ["Messaging"], "Idempotency": ["Replay", "Idempotency"], "Operations": ["Operations", "Drill"]}
BANNED = [  # wording rules from STATION_STANDARD.md
    (r"\balways safe\b", "state a guarantee together with its limit"),
    (r"money (already )?moved", "in a simulation, talk about records, not money moving"),
    (r"follows? the IETF", "cite a draft with its status, not as a rule the API follows"),
]


def main(station_dir):
    st = pathlib.Path(station_dir).resolve()
    problems = []
    need = lambda cond, msg: cond or problems.append(msg)

    m = re.match(r"(\d{3})-[a-z0-9-]+$", st.name)
    if not m:
        sys.exit(f"{st.name}: folder must be NNN-kebab-case-title")
    sid = int(m[1])
    s = ROADMAP.get(sid)
    if not s:
        sys.exit(f"station {sid} is not in curriculum/roadmap.json")

    for f in ["pom.xml", "mvnw", "mvnw.cmd", ".mvn/wrapper/maven-wrapper.properties", "README.md",
              "docs/page.py", "docs/test-run.txt", "docs/capture.sh", "docs/captures/date.txt"]:
        need((st / f).exists(), f"missing {f}")
    need(any((st / "docs" / "captures").glob("0*.txt")), "no captured examples in docs/captures/")

    run = (st / "docs" / "test-run.txt").read_text() if (st / "docs" / "test-run.txt").exists() else ""
    need("BUILD SUCCESS" in run, "docs/test-run.txt is not a passing run (run tools/build_station.sh)")
    need(not re.search(r"Skipped: [1-9]", run) or (st / "docs" / "SKIPPED.md").exists(),
         "tests were skipped: explain each one in docs/SKIPPED.md (honesty rule)")
    classes = re.findall(r"-- in [\w.]*?\.?(\w+)$", run, re.M)

    # The trap test comes first and reproduces the bug.
    need(any("Trap" in c for c in classes), "no *TrapTest: the first test must reproduce the failure before the fix")
    need(any("Contract" in c for c in classes), "no *ContractTest for the HTTP contract (valid, invalid, not found)")
    for t in s["station_types"]:
        words = TYPE_TESTS.get(t, [t])
        need(any(w in c for c in classes for w in words), f"type {t}: no test class named with {' or '.join(words)}")

    if s.get("reviewer_view"):
        need(any((st / "review").glob("*.java")), "reviewer_view station without review/*.java")
        rr = (st / "docs" / "review-run.txt")
        need(rr.exists() and re.search(r"Failures: [1-9]|Errors: [1-9]", rr.read_text()),
             "the flawed version in review/ must fail at least one test (docs/review-run.txt)")

    tests = list((st / "challenge").glob("*Test.java"))
    need(len(tests) >= 2, "Practice needs 2 coding challenges with tests in challenge/")
    need(any((st / "challenge" / "solution").glob("*.java")), "challenge/solution/ is empty")
    cr = st / "docs" / "challenge-run.txt"
    need(cr.exists() and "BUILD SUCCESS" in cr.read_text(), "challenge tests must pass against the solutions (docs/challenge-run.txt)")

    out = ROOT / "exports" / st.name
    for f in ["page.html", "page-standalone.html", "station.json", "starter.zip", "solutions.zip"]:
        need((out / f).exists(), f"missing exports/{st.name}/{f}")
    if (out / "page.html").exists():
        page = (out / "page.html").read_text()
        for tab in TAB_IDS:
            need(f'id="panel-{tab}"' in page, f"page is missing the {tab} tab")
        if s["stage"] == "Production Scale":
            need(re.search(r"runbook", page, re.I) and re.search(r"failure drill", page, re.I),
                 "Production Scale station: Production tab needs a runbook and a failure drill")
        text = re.sub(r"<[^>]+>", " ", page)
        for pattern, rule in BANNED:
            hit = re.search(pattern, text, re.I)
            need(not hit, f"wording: '{hit[0] if hit else ''}' ({rule})")
    if (out / "station.json").exists():
        d = json.loads((out / "station.json").read_text())
        need(d["title"] == s["title"], "station.json title differs from the roadmap")

    readme = (st / "README.md").read_text() if (st / "README.md").exists() else ""
    need(not re.search(r"\b(TODO|FIXME|lorem ipsum)\b", readme, re.I), "README has TODO/FIXME/placeholder text")

    if problems:
        print(f"{st.name}: {len(problems)} problem(s)")
        for p in problems:
            print(" -", p)
        sys.exit(1)
    print(f"{st.name}: OK")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
