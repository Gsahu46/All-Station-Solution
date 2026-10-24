# Station 104 plan: Enterprise integration with Apache Camel

**Problem.** Bimaly (fictional insurance broker): partner banks drop policy files on SFTP at 2 am; 4,000 lines of
custom glue code read them and put the policies on a queue. After a night-time restart, the glue code read every file
in the bank's folder again, and the issuance team received the same policies twice.

**Route.** `sftp://…/upload` (read-only to us: noop=true; name order) → start a run (SHA-256 of the content) →
idempotent consumer on the checksum (on disk) → validate (file-level problems throw BadFileException; bad lines are
rejected with their reason) → all valid lines to `policy.requests` with publisher confirms, messageId BANK:REFERENCE →
run DONE. `GET /integration/runs/{id}`: 200, 404 unknown, 400 not a number.

**Errors.** BadFileException: no retry, the original file to data/dead-letter, run DEAD_LETTERED; the download stays
recorded, so it is not picked up again (its content is not recorded as processed: found in the capture).
Anything else (broker refuses): 3 redeliveries 2 s apart, then run FAILED, not handled, so the file is picked up again
on the next poll. Partial sends are possible on failure; the same messageIds let the reader drop copies.

**Two records on disk.** seen-files.dat (name-size-time: no re-download after a restart) and processed-files.dat
(content checksum: no re-processing after a restart or an identical re-upload). Shortcut: one server's disk.

**Trap.** `FileRestartTrapTest`: a plain Camel route with noop=true reads the same file again after a restart; the
app started twice processes it once, and a re-upload under a new name after the restart is a DUPLICATE.

**Review.** noop=true trusted to remember; one deadLetterChannel for every error.

**Practice.** 1: GET /integration/runs?file=. 2: hold a file with more than 20% of its lines rejected.
3 (paper): two servers polling the same folder.

**Simulation.** The bank's SFTP server is atmoz/sftp in Docker; the bank, customers and files are demo data.
