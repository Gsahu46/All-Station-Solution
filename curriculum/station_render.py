"""Render one station: its page (HTML), README.md and station.json, from the station's docs/page.py.

    python3 curriculum/station_render.py stations/085-idempotent-upi-payments OUT_DIR

page.py holds only the station's content. It runs with every helper below already in scope
(code, read, run, belongs, table, filebrowser, dwn, e, pretty, capture, examples, challenge, ST, STATION_RUN, N_TESTS) and must define:
    META   = {"id": 85, "stack": "...", optional "simulation", "label", "show_blueprint", "package"}
    LEVELS = [("1", "Understand", [(tab_id, label, sections, html), ...]), ("2", "Build", [...]), ("3", "Go deeper", [...])]
Header facts (title, stage, types, before/after) come from curriculum/roadmap.json, so they never drift from the roadmap.
Code, tests and captures are read from the station folder, so the page always shows the exact files that passed.
"""
import base64
import html
import json
import pathlib
import re
import shlex
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROADMAP = {s["id"]: s for s in json.loads((HERE / "roadmap.json").read_text())["stations"]}
e = html.escape
ST = None  # the station folder, set by main()


def code(text, lang):
    return f'<pre class="code"><code class="language-{lang}">{e(text.rstrip())}</code></pre>'


def read(rel):
    return (ST / rel).read_text()


def lang_of(name):
    return {"java": "java", "sql": "sql", "yaml": "yaml", "yml": "yaml", "xml": "xml", "json": "json",
            "properties": "properties", "sh": "bash", "kt": "kotlin", "tf": "hcl"}.get(name.rsplit(".", 1)[1], "text")


def run(name):
    """Parse a saved Maven run in docs/: per-class (passed, total), then passed, total and the raw text."""
    text = (ST / "docs" / name).read_text()
    per = {}
    for m in re.finditer(r"Tests run: (\d+), Failures: (\d+), Errors: (\d+), Skipped: \d+.*? -- in [\w.]*?\.?(\w+)$", text, re.M):
        n, f, er, cls = int(m[1]), int(m[2]), int(m[3]), m[4]
        per[cls] = (n - f - er, n)
    total = sum(t for _, t in per.values())
    passed = sum(p for p, _ in per.values())
    return per, passed, total, text


def pretty(text):
    try:
        return json.dumps(json.loads(text), indent=2, ensure_ascii=False)
    except ValueError:
        return text


def capture(name):
    """docs/captures/NAME.txt as (request, response) text for code(..., "http").
    capture.sh writes the first line as "$ curl" plus single-quoted args, so shlex can split it."""
    first, rest = read(f"docs/captures/{name}.txt").split("\n", 1)
    method, headers, body, url = None, [], None, ""
    args = iter(shlex.split(first[len("$ curl"):]))
    for a in args:
        if a == "-X":
            method = next(args)
        elif a == "-H":
            headers.append(next(args))
        elif a == "-u":  # demo credentials only: shown as the header curl actually sends
            headers.append("Authorization: Basic " + base64.b64encode(next(args).encode()).decode())
        elif a in ("-d", "--data-raw"):
            body = next(args)
        elif a == "--data-binary":  # "@path" relative to docs/captures, where capture.sh runs: show the file sent
            v = next(args)
            body = (ST / "docs/captures" / v[1:]).resolve().read_text() if v.startswith("@") else v
        elif a.startswith("http"):
            url = a
    method = method or ("POST" if body is not None else "GET")
    req = f"{method} {re.sub(r'^https?://[^/]+', '', url)} HTTP/1.1" + "".join("\n" + h for h in headers)
    req += f"\n\n{pretty(body)}" if body else ""
    head, _, rbody = rest.strip().partition("\n\n")
    return req, head.strip() + (f"\n\n{pretty(rbody.strip())}" if rbody.strip() else "")


def examples(items):
    """items: (capture name, title, why). Request and response side by side, both from the real capture."""
    out = []
    for name, title, why in items:
        req, resp = capture(name)
        out.append(f'<section class="example"><h3>{title}</h3><p>{why}</p><div class="pair">'
                   f'<div><p class="eyebrow">Request</p>{code(req, "http")}</div>'
                   f'<div><p class="eyebrow">Response</p>{code(resp, "http")}</div></div></section>')
    return "".join(out)


def challenge(n, title, level, minutes, task, done, hints, test, solutions):
    """One Practice coding challenge: the task, hints, the ready test, and the solution behind a click."""
    sol = "".join(f'<p class="path">{e(f)}</p><div class="src">{code(read(f), lang_of(f))}</div>' for f in solutions)
    hint = "".join(f"<li>{h}</li>" for h in hints)
    return (f'<section class="challenge"><p class="eyebrow">Challenge {n} · {level} · about {minutes} minutes</p><h2>{title}</h2>'
            f'<p>{task}</p><p><b>Done when:</b> {done}</p>'
            f'<details class="qa"><summary>Hints</summary><ul>{hint}</ul></details>'
            f'<p class="path">{e(test)}</p>{code(read(test), "java")}'
            f'<details class="qa solution"><summary>Solution (open after trying)</summary>{sol}</details></section>')


def belongs(sections, rule):
    items = "".join(f"<li>{s}</li>" for s in sections)
    return f'<aside class="belongs"><p class="eyebrow">Belongs in this tab</p><ul>{items}</ul><p class="rule">{rule}</p></aside>'


def table(head, rows, cls=""):
    th = "".join(f"<th>{h}</th>" for h in head)
    tr = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="scroll"><table class="{cls}"><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'


def filebrowser(group, files):
    """files: list of (path, notes_html). Left: file names. Right: the file, with its notes above it."""
    btns, panes = [], []
    for i, (path, notes) in enumerate(files):
        name = path.rsplit("/", 1)[-1]
        fid = f"{group}-{i}"
        sel = "true" if i == 0 else "false"
        btns.append(f'<button class="file-btn" role="tab" id="{fid}-b" aria-controls="{fid}" aria-selected="{sel}" data-group="{group}">{e(name)}</button>')
        hidden = "" if i == 0 else " hidden"
        panes.append(f'<div class="file-pane" role="tabpanel" id="{fid}" aria-labelledby="{fid}-b"{hidden}>'
                     f'<p class="path">{e(path)}</p><div class="notes">{notes}</div><div class="src">{code(read(path), lang_of(path))}</div></div>')
    return f'<div class="files"><div class="file-list" role="tablist" aria-label="Files">{"".join(btns)}</div><div class="file-body">{"".join(panes)}</div></div>'


def dwn(does, why, without, extra=""):
    """Code walkthrough notes for one class: what it does, why it exists, what breaks without it."""
    return f'<dl class="dwn"><dt>Does</dt><dd>{does}</dd><dt>Why</dt><dd>{why}</dd><dt>Without it</dt><dd>{without}</dd></dl>{extra}'


BLUEPRINT = [
    ("1 · Understand", "Understand", "The real-life story, what we build, an everyday analogy, how it works in 4 steps, a check-yourself question, what the station is not, key terms", "About 5 minutes, no code"),
    ("2 · Build", "Spec", "Business problem, acceptance criteria (Given/When/Then), requirements, learning objectives", "Always"),
    ("", "API contract", "Endpoints, fields, status codes, the retry rule, error format; real captured examples, each with why the API answered that way", "Always"),
    ("", "Edge cases & trap", "Every edge case mapped to its test; the plausible-but-wrong approach, shown failing", "Always"),
    ("", "Set up & code", "What to install, commands for Windows and macOS/Linux, try-it commands with expected results, troubleshooting; every file in request order with what it does, why, and what breaks without it", "Always"),
    ("", "Tests", "Required tests for the station's types, the saved real run, every test file", "Always"),
    ("", "Practice", "2 coding challenges with ready tests and hidden solutions; design-on-paper tasks", "Always"),
    ("3 · Go deeper", "Design", "Numbered approach, sequence diagram, alternatives with costs, database design and transaction boundary", "Always; database part when there is a database"),
    ("", "Production", "Security, performance, reliability, scale, cost, maintainability; full runbook and failure drill", "Always; runbook only at Production Scale"),
    ("", "Interview", "Questions with hidden strong answers, self-check rubric", "Always"),
    ("", "Review", "A flawed version, findings, and the real test results against it", "Stations marked reviewer view (123 of 200)"),
]
BLUEPRINT_INTRO = ("<p>Every one of the 200 stations uses the same tabs; only the depth changes with the stage. <strong>Understand</strong> takes about 5 minutes "
                   "and has no code. <strong>Build</strong> is the hands-on part. <strong>Go deeper</strong> is the engineering a 2–3 year developer is expected to explain.</p>")


def header(meta):
    s = ROADMAP[meta["id"]]
    num = f'{s["id"]:03d}'
    after = [r for r in ROADMAP.values() if s["id"] in r.get("prerequisites", [])]
    linked = lambda rows: " · ".join(f'{r["id"]:03d} {e(r["title"])}' for r in rows) or "None"
    meta_items = [("Stage", s["stage"]), ("Experience", s["suggested_experience"].replace("-", "–")), ("Track", s["track"]),
                  ("Industry", s["industry"]), ("Types", " · ".join(s["station_types"]) or "None"),
                  ("Reviewer view", "Yes" if s.get("reviewer_view") else "No")]
    sim = (f'\n    <p class="sim"><b>Simulation</b><span>{meta["simulation"]}</span></p>' if meta.get("simulation") else "")
    return (f'<header class="station">\n'
            f'    <span class="num">STATION {num}{" · " + meta["label"] if meta.get("label") else ""}</span>\n'
            f'    <h1>{e(s["title"])}</h1>\n'
            f'    <p class="scenario">{e(s["scenario"])}</p>{sim}\n'
            f'    <ul class="meta">\n' + "".join(f'      <li><b>{k}</b>{e(v)}</li>\n' for k, v in meta_items) +
            f'    </ul>\n'
            f'    <div class="links">\n'
            f'      <p><span class="eyebrow">Before this</span><br>{linked([ROADMAP[p] for p in s.get("prerequisites", [])])}</p>\n'
            f'      <p><span class="eyebrow">Builds toward</span><br>{linked(sorted(after, key=lambda r: r["id"]))}</p>\n'
            f'      <p><span class="eyebrow">Stack</span><br>{meta["stack"]}</p>\n'
            f'    </div>\n'
            f'  </header>'), f'Station {num} · {s["title"]}'


def blueprint_block(show):
    if not show:
        return ""
    rows = [[f"<strong>{lv}</strong>" if lv else "", f"<strong>{t}</strong>", w, c] for lv, t, w, c in BLUEPRINT]
    return ('  <details class="blueprint" open>\n'
            '    <summary>Page blueprint: 11 tabs in 3 levels, and what goes in each</summary>\n'
            f'    {BLUEPRINT_INTRO}\n'
            f'    {table(["Level", "Tab", "What goes in it", "When"], rows)}\n'
            '  </details>\n\n')


def main(station_dir, out_dir):
    global ST
    ST = pathlib.Path(station_dir).resolve()
    out = pathlib.Path(out_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)

    station_run = run("test-run.txt")
    assert station_run[1] == station_run[2] > 0, "docs/test-run.txt must be a passing run"
    ns = dict(globals(), ST=ST, STATION_RUN=station_run, N_TESTS=station_run[2])
    page_py = ST / "docs" / "page.py"
    exec(compile(page_py.read_text(), str(page_py), "exec"), ns)
    meta, levels = ns["META"], ns["LEVELS"]
    tabs = [t for _, _, ts in levels for t in ts]

    first = tabs[0][0]
    tabbar = "".join(
        f'<span class="grp" role="presentation">{num} · {name}</span>' + "".join(
            f'<button role="tab" id="tab-{k}" aria-controls="panel-{k}" aria-selected="{"true" if k == first else "false"}" tabindex="{0 if k == first else -1}" data-tab="{k}">{label}</button>'
            for k, label, _, _ in ts)
        for num, name, ts in levels)
    panels = "".join(
        f'<section role="tabpanel" id="panel-{k}" aria-labelledby="tab-{k}" class="panel"{"" if k == first else " hidden"}>{body}</section>'
        for k, _, _, body in tabs)
    head_html, title = header(meta)

    page = (HERE / "station_page_template.html").read_text()
    page = (page.replace("%%TITLE%%", e(meta.get("page_title", title))).replace("%%HEADER%%", head_html)
                .replace("%%BLUEPRINT%%", blueprint_block(meta.get("show_blueprint", False)))
                .replace("%%TABS%%", tabbar).replace("%%PANELS%%", panels))
    assert "%%" not in page, "unfilled placeholder in the template"
    (out / "page.html").write_text(page)  # body content, for hosts that add their own document skeleton (claude.ai artifacts)
    (out / "page-standalone.html").write_text(  # a complete document, for any website or for opening from disk
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        '<style>body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style></head><body>\n'
        + page + '\n</body></html>\n')

    # station.json: the same content as data, for a site that renders stations with its own components.
    s = ROADMAP[meta["id"]]
    (out / "station.json").write_text(json.dumps({
        "id": s["id"], "slug": ST.name, "title": s["title"], "scenario": s["scenario"], "stage": s["stage"],
        "experience": s["suggested_experience"], "track": s["track"], "industry": s["industry"],
        "types": s["station_types"], "reviewer_view": bool(s.get("reviewer_view")), "prerequisites": s.get("prerequisites", []),
        "stack": meta["stack"], "simulation": meta.get("simulation"),
        "tests": {"passed": station_run[1], "total": station_run[2]},
        "levels": [{"level": num, "name": name, "tabs": [{"id": k, "label": label, "sections": secs, "html": body}
                                                          for k, label, secs, body in ts]} for num, name, ts in levels],
    }, ensure_ascii=False, indent=1))

    # README.md for the learner download: same content, minus page chrome, source code (it is in the files) and solutions.
    body = "".join(f"<h1>{num} · {name}{'' if label == name else ': ' + label}</h1>{content}" for num, name, ts in levels for _, label, _, content in ts)
    body = re.sub(r'<aside class="belongs">.*?</aside>', "", body, flags=re.S)
    body = re.sub(r'<div class="src">.*?</pre></div>', "", body, flags=re.S)
    body = re.sub(r'<div class="file-list".*?</div>', "", body, flags=re.S)
    body = re.sub(r'<p class="path">(.*?)</p>', r'<h4><code>\1</code></h4>', body)
    body = re.sub(r'<details class="qa solution">.*?</details>',
                  "<p><em>Solution: in the separate solutions pack. Try first.</em></p>", body, flags=re.S)
    sim = f"<p><strong>Simulation:</strong> {meta['simulation']}</p>" if meta.get("simulation") else ""
    readme_head = (f"<h1>{e(title)}</h1>"
                   f"<p>{s['stage']} · {s['suggested_experience'].replace('-', '–')} · {s['track']} · {s['industry']} · Types: {', '.join(s['station_types']) or 'none'}</p>"
                   f"<p>{meta['stack']}. {meta.get('readme_requirements', 'Needs JDK 25 (or 21, see Set up & code) and Docker. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).')}</p>"
                   f"{sim}"
                   f"<p>Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run <code>./mvnw test</code> for all {station_run[2]} tests.</p>")
    md = subprocess.run(["pandoc", "-f", "html", "-t", "gfm-raw_html", "--wrap=none"], input=readme_head + body,
                        capture_output=True, text=True, check=True).stdout
    (ST / "README.md").write_text(re.sub(r"\n{3,}", "\n\n", md))
    print(f"rendered {ST.name}: page.html, station.json -> {out}; README.md -> station folder ({station_run[2]} tests)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
