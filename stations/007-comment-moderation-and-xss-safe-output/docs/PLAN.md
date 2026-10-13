# Station 007 plan: Comment moderation and XSS-safe output

**Problem.** Chaupal showed a comment's <script> as live HTML; banned words pass as "b@d"; a substring filter blocked "scampi".

**Endpoints.** `POST /posts/{id}/comments` (members) 201 / 400 / 401 / 403 muted / 404 (also another's private post) /
422 community-rules / 429 + Retry-After. `GET /posts/{id}/comments` JSON (raw text) or text/html (encoded, CSP header).

**Data.** No database. Two posts (one private), four demo users, comments in memory, per-user sliding-window rate limit (5/60s).

**Trap.** Input blocklist filter. `InputFilterTrapTest`: <img onerror> passes; <scr<script>ipt> becomes <script>.
Real API stores as typed and encodes on output.

**Tests.** Trap, `CommentContractTest`, `CommentSecurityTest` (7 payloads), `ModerationTest` (disguises, scampi, limits, Turkish).

**Review.** review/CommentService (input regex filter, list without visibility), CommentHtml (no encoding), Moderation
(substring). 16 tests fail.

**Practice.** 1: **bold** with encode-then-format. 2: report a comment, 3 reporters hide it. Design: clickable links.
