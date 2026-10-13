"""Renders the roadmap review page from roadmap.json into the given HTML file (keeps its <head> styles and script)."""
import json, html, os, sys
W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F = sys.argv[1]
doc = json.load(open(os.path.join(W, "curriculum", "roadmap.json"))); R = doc["stations"]; E = html.escape
NEW_ROUND = max(r["round"] for r in R)
LV = {"0-1": ("Foundations", "suggested 0–1 years", "APIs, validation, errors, core Java, Spring basics, SQL, JDBC, JPA, calling other APIs"),
      "0-2": ("Working Systems", "suggested 0–2 years", "transactions, security, payments, search, files, messaging basics, integrations, AI features"),
      "2-3": ("Production Scale", "suggested 2–3 years", "Redis, Kafka, AI agents, AWS, services, resilience, observability, delivery, money at scale")}
infra_label = lambda s: "no external services" if s == "none" else s.replace("+", " · ")
sections = []
for lv, (name, years, blurb) in LV.items():
    rows = [r for r in R if r["level"] == lv]; items = []
    for r in rows:
        pre = ", ".join(f"{p:03d}" for p in r["prerequisites"]) or "none"
        eps = "".join(f"<code>{E(e)}</code>" for e in r["endpoints"])
        tags = "".join(f"<li>{E(c)}</li>" for c in r["concepts"])
        spec = r["track"] == "Specialisation"; new = r["round"] == NEW_ROUND
        badges = ('<span class="new">Optional</span>' if spec else "") + ('<span class="new">New</span>' if new else "")
        types = ", ".join(r["station_types"]) or "API only"
        ms = "".join(f"<li>{E(m)}</li>" for m in r.get("milestones", []))
        ms = f'<ol class="ms">{ms}</ol>' if ms else ""
        search = E(" ".join([r["title"], r["industry"], r["company"], r["scenario"], r["trap"], " ".join(r["concepts"]),
                             " ".join(r["endpoints"]), r["infra"], types, "optional" if spec else "core", "new" if new else ""]).lower())
        items.append(f'''<li class="st" data-level="{lv}" data-new="{'1' if new else '0'}" data-search="{search}">
  <div class="num">{r["id"]:03d}</div>
  <div class="body">
    <h3>{E(r["title"])}{badges}</h3>
    <p class="meta">{E(r["industry"])} · {E(r["company"])} · {E(infra_label(r["infra"]))}</p>
    <p class="scen">{E(r["scenario"])}</p>
    <p class="trap"><b>Trap:</b> {E(r["trap"])}</p>
    <div class="eps">{eps}</div>
    <ul class="tags">{tags}</ul>{ms}
    <p class="pre">Tests: {E(types)} · Reviewer view: {"yes" if r["reviewer_view"] else "no"} · Concepts from: {pre}</p>
  </div>
</li>''')
    ns = sum(1 for r in rows if r["track"] == "Specialisation"); nn = sum(1 for r in rows if r["round"] == NEW_ROUND)
    sections.append(f'''<section class="lv" data-level="{lv}" id="level-{lv}">
  <header class="lvh"><span class="chip c{lv.replace('-','')}">{years}</span><h2>{name}</h2><p>{len(rows)} stations ({nn} new, {ns} optional) · {E(blurb)}</p></header>
  <ol class="list">{''.join(items)}</ol>
</section>''')
cnt = {l: sum(1 for r in R if r["level"] == l) for l in LV}
page = open(F).read()
head = page[:page.index('<div class="wrap">')]; script = page[page.index('<script>'):]
body = f'''<div class="wrap">
  <h1>200 API &amp; Backend Engineering Stations</h1>
  <p class="lede">Standalone Spring Boot 4 projects on Java 25, each solving its own real-world problem, from a first endpoint to production systems. Every station names the trap it teaches and the tests it must pass. Companies are fictional and inspired by real industries. Finishing the stations builds the skills, judgement and portfolio for backend roles; it is not the same as years of production experience.</p>
  <ul class="facts"><li><b>200</b><span>stations</span></li><li><b>{cnt["0-1"]}</b><span>Foundations</span></li><li><b>{cnt["0-2"]}</b><span>Working Systems</span></li><li><b>{cnt["2-3"]}</b><span>Production Scale</span></li><li><b>{sum(r["round"]==NEW_ROUND for r in R)}</b><span>new after the industry research</span></li><li><b>{sum(r["track"]=="Specialisation" for r in R)}</b><span>optional</span></li></ul>
  <div class="changes">
    <h2>What changed after the industry research</h2>
    <ul>
      <li>New: an MCP server for AI agents, a tool-calling agent with guardrails, an AI gateway, and RAG with an evaluation set in place of plain vector search.</li>
      <li>New: change data capture with Debezium, cell-based architecture, relationship-based document sharing, and passkeys in place of TOTP-only login.</li>
      <li>New for India and banks: card tokenisation, UPI AutoPay mandates, Account Aggregator consent and ISO 20022 messages; DPDP rules in the data-deletion station.</li>
      <li>New for services firms: Apache Camel integration and COBOL-to-Java with characterisation tests; plus mutation, property-based and architecture tests.</li>
      <li>Updated for Spring Boot 4, Java 25 and Kafka 4: built-in API versioning and retries, HTTP service clients, Jackson 3, OpenTelemetry, SLO burn-rate alerts, OpenFeature, Valkey, and the LocalStack account change.</li>
      <li>Thirteen overlapping stations were merged into their neighbours to keep the total at 200.</li>
    </ul>
  </div>
  <div class="bar" role="toolbar" aria-label="Filter stations">
    <button type="button" id="f-all" data-f="all" aria-pressed="true">All</button>
    <button type="button" id="f-01" data-f="0-1" aria-pressed="false">Foundations</button>
    <button type="button" id="f-02" data-f="0-2" aria-pressed="false">Working Systems</button>
    <button type="button" id="f-23" data-f="2-3" aria-pressed="false">Production Scale</button>
    <button type="button" id="f-new" data-f="new" aria-pressed="false">New only</button>
    <input id="q" type="search" placeholder="Search: MCP, kafka, passkeys, UPI, payments…" aria-label="Search stations">
    <span class="count" id="count">200 shown</span>
  </div>
  {''.join(sections)}
  <p class="empty" id="empty" hidden>No station matches. Try another word.</p>
</div>
'''
open(F, "w").write(head + body + script); print("page written")
