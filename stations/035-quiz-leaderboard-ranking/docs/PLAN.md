# Station 035 plan: Quiz leaderboard ranking

**Problem.** Shikshalab's leaderboard ranked by list position, so two students with 88 got ranks 3 and 4. A quick fix
shared ranks but kept "rank <= 10" as the top 10, so a tie at 10th showed 11 names.

**Endpoints.** `GET /quizzes/{id}/leaderboard?top=10` (1 to 100) 200 {quizId, title, participants, rows[{rank,
denseRank, studentId, name, score, seconds}], moreTiedAtCutoff}; `GET /quizzes/{id}/leaderboard/me` with
X-Student-Id (demo stand-in for the login) 200 {…, rank, denseRank, participants}; 404 quiz or attempt; 400 bad top,
missing or malformed header.

**Rules.** Rank by score only (competition: 1,2,2,4; dense alongside). Display order inside a tie: faster first, then
student id (`ORDER = comparingInt(score).reversed().thenComparingInt(seconds).thenComparing(studentId)`). Top N =
at most N rows via a PriorityQueue of N+1 with `ORDER.reversed()`; ties beyond the cut are counted. "Me" =
1 + count(score > mine), dense = 1 + distinct higher scores.

**Data.** Quiz 3 "Algebra sprint": 12 students, ties at 3rd, 6th and 10th. Quiz 7: 2,000 seeded attempts.

**Trap.** `ListPositionRankTrapTest`: positions give 3 and 4; the quick fix shows 11; the fix shows 10, shared
ranks, and moreTiedAtCutoff 1. Mutations: rank by position -> 4 red; heap keeps the worst -> 9; no time tie-break ->
1; no cutoff count -> 4; "me" counts ties as ahead -> 2; dense = competition -> 2.

**Tests.** Trap; `RankingTest` (hand-checked ranks, id tie-break, the reversed() slip, heap vs full sort for 6 sizes,
me agrees with the board for 100 students, cutoff count); `LeaderboardContractTest`.

**Practice.** 1: the rows around me. 2: best of several attempts. Design: a live leaderboard for 2 lakh students.
