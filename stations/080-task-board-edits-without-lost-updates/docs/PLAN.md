# Station 080 plan: Task board edits without lost updates

**Problem.** Two Taskloom managers edit one card at once; the second save silently replaces the first (last write wins).

**Endpoints.** `GET /tasks/{id}`: the task with `ETag: "<version>"` (strong); If-None-Match with the current ETag is
304 (Spring MVC does this for a ResponseEntity with an ETag). `PUT /tasks/{id}` with `If-Match: "<version>"` and the
full body {title 1-120, description, status open|doing|done, assignee}: 200 with the next ETag; no If-Match 428; an
old or malformed ETag 412; a title already on the board 409 (the copy is current, the edit breaks a rule); unknown 404;
bad body 400.

**Concurrency.** Spring Data JDBC `@Version` on the Task record: save issues UPDATE ... WHERE id = ? AND version = ?
and throws OptimisticLockingFailureException when no row matches, so the check and the write are one statement.
The change and its activity row (task_changes) are one transaction.

**Database.** tasks (status, title length, version >= 0, unique board+title); task_changes (one per task version);
trigger tasks_version_must_increase: every UPDATE must move the version on by exactly one, so a version-less writer
(the old code) is refused by the database itself.

**Trap.** `LastWriteWinsTrapTest`: the old board drops one manager's change; the API refuses the second save of the same
version with 412, nothing is lost, and the re-read edit lands on top.

**Concurrency tests.** Ten PUTs of version 0 at once (virtual threads, one latch): exactly one 200, nine 412, version 1,
one activity row. Ten editors that read, edit and retry on 412: all ten changes land, version 10.

**Found while building.** (1) Spring Data JDBC throws OptimisticLockingFailureException and DuplicateKeyException
unwrapped: a cause-chain walk changed no test and was replaced by two catch clauses. (2) Spring MVC already answers
If-None-Match for a ResponseEntity with an ETag (a planned challenge passed with no code): now a station test. (3) A
`SELECT setval(...)` in the demo migration made JdbcClient.update() fail when tests reload it ("A result was returned
when none was expected"); `ALTER ... RESTART WITH` instead. (4) Without @Version every edit fails on the trigger ("version 0 to 0"): an error, not a silent overwrite.

**Mutations.** no @Version -> 6; If-Match ignored (save on current version) -> 2; no transaction -> 1; no 428 -> 1;
no version trigger -> 1.

**Review.** Save on top of the latest version ("no more read it again errors"), If-Match optional for the mobile
app: 3 of 14 fail.

**Practice.** 1: PATCH with JSON merge patch, same If-Match rules. 2: DELETE with If-Match (412 when changed since).
3 (paper): merging field-level changes instead of refusing, and live collaboration (CRDTs, operational transform).
