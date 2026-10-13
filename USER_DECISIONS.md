# User decisions that override LOOP_PROMPT.md

## 2026-10-10 12:18 IST — restart with standalone real-world APIs
The user said: "Maine ye saare stations use karne nhi bola tha, maine bola tha real world scenarios k naye APIs banao."
Clarified with two questions:
1. Remove everything tied to the old 100 stations: no viewer/site format (station.json for "Paradox Line", site export, render checks),
   no old-to-new mapping or originality comparison, no old numbering or references.
2. Rebuild all stations. Make a new roadmap first and get it approved before building.

What this changes in LOOP_PROMPT.md:
- §3.1/§5.1: no station.json for the viewer and no site/ export. Each station is a standalone Spring Boot project whose
  README.md carries the 12 VISION §6 sections (problem, requirements, objectives, API contract, edge cases, approach,
  code, code explanation, database, testing, real-world considerations, interview takeaways).
- S1 discovery of the old site, S4 render checks, originality.md, old-to-new.json, old_stations.json: dropped.
- Every station is its own API for its own business problem. It never extends or refactors another station's code;
  prerequisites are about concepts only.
- Levels stay 30/30/40 (0-1 / 0-2 / 2-3). Code quality, test and verification rules in §5.2–5.4 still apply.

Previous work (14 stations, site export, old curriculum) is kept, untouched, in archive/v1-2026-10-10/.

## 2026-10-10 12:52 IST — 150 stations
User: "Perfect ... Par ismai aur 50 high value APIs banao aur mujhe dikhao." Roadmap grows to 150 (45/45/60). Still waiting for approval before building.

## 2026-10-10 13:09 IST — job readiness, at most 200
User: finishing all stations should make a person ready for every real-world problem in the IT field; every concept clear; no fixed count but never more than 200. Roadmap grows to 199 (56/62/81 ≈ 28/31/41 %), adding AWS (Terraform, SQS, SNS, Lambda, DynamoDB, Secrets Manager, CloudWatch, LocalStack) and other job-readiness gaps. Still waiting for approval before building.

## 2026-10-10 13:36 IST — apply the review
User shared an external review and said "Improve it and give it to me". Applied all roadmap-level items: 088 failover fixed (status check before failover), a trap for every station, dated configuration for EMI/GST/tax, station 119 API security audit (total 200), stage names with years as a suggestion, Core vs Specialisation track, honest job-readiness wording, station types + required tests, reviewer view for advanced stations, five milestones per capstone. STATION_STANDARD.md is the build template. Staged capstones and reviewer views were taken as approved by "improve it" (they were the two open decisions); stations themselves stay standalone.

## 2026-10-11 01:03 IST — apply the industry research
User: "So do these changes and give the latest 200 api list". Applied curriculum/round5.py: 13 merges, 13 additions, TOTP → passkeys, 4 renames, ~45 updates. Baseline Java 25 + Spring Boot 4. Roadmap v3.0, 54/64/82, 189 core / 11 optional.

## 2026-10-11 01:33 to 12:18 IST — station 085 as the format
User asked for one API solved completely to see the tabs a station needs, then sent three external reviews. All applied;
every accepted point became a rule in STATION_STANDARD.md (three levels, 11 tabs, retry and replay wording, simulations,
guarantees with limits, DB constraints mirroring Java rules, Locale.ROOT, starter and solutions packs).

## 2026-10-11 12:39 IST — build all 200 with Claude Code, integrate into the website
User: "Mujhe ab loop prompt aur iss conversation ka context do taki mai Claude code sai in 200 APIs ka solution banwa k
apne project mai direct integrate kar pau jo ki Claude design mai hai." Taken as approval of roadmap v3.0 and of
station 085 as the format. Roadmap locked. Build order: roadmap order from 001, one station per iteration.
Integration goes through INTEGRATION_MAP.md, written once from the real website project (see INTEGRATION.md).
