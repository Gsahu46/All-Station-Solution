# Integration: getting built stations into the owner's website

The website was designed in Claude Design. Its structure was not visible from the session that wrote this kit, so the
kit does not guess. It produces a fixed set of files per station (the **export contract** below), and a one-time setup
step lets Claude Code look at the real website project and write `INTEGRATION_MAP.md`: where each file goes and what
list or menu to update. Every iteration then follows that map, and touches nothing else.

## The export contract (stable; the website can rely on it)

```
exports/index.json                     every built station: id, slug, title, stage, experience, track, types, tests
exports/NNN-slug/page.html             the station page as body content (for hosts that add <html>/<head>, like claude.ai artifacts)
exports/NNN-slug/page-standalone.html  the same page as a complete HTML document (for any website, or open from disk)
exports/NNN-slug/station.json          the same content as data: header facts + levels -> tabs -> html, test counts
exports/NNN-slug/starter.zip           learner download: the Maven project, README, challenge tests, no solutions
exports/NNN-slug/solutions.zip         the challenge solutions, to unlock after an attempt
```

`station.json` shape:
```json
{ "id": 85, "slug": "085-idempotent-upi-payments", "title": "...", "scenario": "...", "stage": "Working Systems",
  "experience": "0-2 years", "track": "Core", "industry": "Payments", "types": ["Database", "..."],
  "reviewer_view": true, "prerequisites": [8, 55], "stack": "...", "simulation": "html or null",
  "tests": { "passed": 31, "total": 31 },
  "levels": [ { "level": "1", "name": "Understand", "tabs": [ { "id": "understand", "label": "Understand", "sections": "0", "html": "..." } ] },
              { "level": "2", "name": "Build", "tabs": [ "spec", "api", "trap", "code", "tests", "practice" ] },
              { "level": "3", "name": "Go deeper", "tabs": [ "design", "production", "interview", "review" ] } ] }
```
The tab `html` uses the class names styled in `curriculum/station_page_template.html` (`belongs`, `rulebox`, `dwn`,
`pill ok|warn|bad`, `code`, `files`, `qa`, `solution`, ...). A site that renders `station.json` with its own components
should copy that CSS or map those classes to its own design tokens.

## Pick the route that matches where the website lives

**A. The website is code on disk** (a repository, or files exported/downloaded from Claude Design).
Run the one-time setup below with that folder's path. This is the route that allows "build a station, and it appears
on the site" with no manual step.

**B. The website exists only inside claude.ai** (a design you cannot download as files).
Claude Code cannot edit it from your computer. Either export or download it as files first and use route A, or keep the
design as the front door and link each station to its own published page: each `page.html` can be published as its own
artifact from a claude.ai chat, and `exports/index.json` is the list to link from.

**C. The website renders data.** Point it at `exports/index.json` and each `station.json`; then integration is only
"copy the exports folder", and the map says so.

## One-time setup (route A or C): paste this into Claude Code in this kit folder

```
Read CLAUDE.md and INTEGRATION.md. My website project is at: <ABSOLUTE PATH TO THE WEBSITE FOLDER>.
Look at it read-only first: framework or plain HTML, where pages live, how a list of items (stations, lessons,
projects) is shown, how static files and downloads are served, how it is built and previewed, and whether it is a git repo.
Then write INTEGRATION_MAP.md in this kit folder with:
1. Where exports/NNN-slug/ files go in the website (exact paths), and which one is used (page-standalone.html,
   page.html inside the site's layout, or station.json rendered by the site's components).
2. Exactly which file lists the stations and how to add or update one entry from exports/index.json.
3. The command to build or preview the site, and how to check that a station page shows.
4. Safety: work on a git branch named stations/import if the site is a repo; add or update only the paths in (1) and
   the list in (2); never delete or restyle anything else.
Then integrate station 085 only, following the map, run the site's build or preview, and show me what changed.
Do not integrate any other station until I confirm 085 looks right.
```

After the owner confirms 085, every loop iteration runs step 9 of `LOOP_PROMPT.md` (integrate one station by the map).

## Keeping the site and the stations in step

- The roadmap page (all 200 titles) is `curriculum/roadmap-source/render_page.py`; built stations are in `exports/index.json`.
  A site can mark stations as "available" by checking which ids are in `index.json`.
- Re-building a station (`tools/build_station.sh`) rewrites its exports; integration then overwrites the same paths.
- Solutions are a separate file on purpose: offer `solutions.zip` only after the learner has tried (or behind a click).
