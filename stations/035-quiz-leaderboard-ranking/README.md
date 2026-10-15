# Station 035 · Quiz leaderboard ranking

Foundations · 0–1 years · Core · Edtech · Types: none

Spring Boot 4.1.1 · Java 25 · Comparator chains · PriorityQueue top-N · competition and dense ranking · MockMvc. Needs JDK 25 (or 21, see Set up & code). No Docker, no database. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Quizzes, students and scores are demo data, not Shikshalab's. The X-Student-Id header stands in for a signed-in student; a real app takes the student from the login, never from a header.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 19 tests.

# 1 · Understand

## The problem in real life

1.  **Two students, one score**

    Kabir and Meera both score 88. The board shows Kabir 3rd and Meera 4th, only because of the order rows came back in. Meera's parents write in.

2.  **A quick fix, a new bug**

    Equal scores now share a rank, and "top 10" becomes "rank 10 or better". When two students tie for 10th, the top 10 shows 11 names.

3.  **The fix**

    Rank by score so ties share a rank; show at most N rows, ordered by score, then time, then id; say how many tied students did not fit.

A rank comes from the score, not from where a row happens to sit in a list.

## What are we building?

`GET /quizzes/{id}/leaderboard?top=10` shows the best students with their ranks, and `…/leaderboard/me` shows a student their own rank among everyone.

## An everyday analogy

A school sports day. Two children tie for silver: both get silver, and the next child is 4th. The notice board has room for ten names; if there are two 10th places, the board says "and 1 more tied" instead of squeezing in an eleventh.

## How it works in 4 steps

1.  **Order** attempts: higher score first, then less time, then student id.
2.  **Keep the best N** with a small heap, without sorting all 2,000.
3.  **Give ranks**: equal scores share the rank of the first of them.
4.  **Count** how many students tied with the last row did not fit.

Check yourself: Saanvi and Reyansh both scored 70. Saanvi took 240 seconds, Reyansh 270. What are their ranks?

Both 10th: ranks come from the score. Saanvi is shown first because she was faster, and in a top 10 she is the one that fits.

## What this station is not

- **No live updates.** The board is computed per request.
- **No login.** A header stands in for the signed-in student.
- **One attempt per student.** Challenge 2 allows retries.

## Key terms

| Term                      | Simple meaning                                                          | Everyday example                                                   | In this project             |
|---------------------------|-------------------------------------------------------------------------|--------------------------------------------------------------------|-----------------------------|
| **Competition ranking**   | Equal scores share a rank, and the next rank skips: 1, 2, 2, 4.         | Two runners tie for silver; nobody gets bronze; the next is 4th.   | `rank`                      |
| **Dense ranking**         | Equal scores share a rank, and the next rank does not skip: 1, 2, 2, 3. | Counting distinct scores above you.                                | `denseRank`                 |
| **Tie-break**             | A rule that orders equal items, here only for display.                  | Who finished first, among equal marks.                             | time taken, then student id |
| **Comparator**            | A rule that says which of two items comes first.                        | The judging criteria, in order.                                    | `Leaderboard.ORDER`         |
| **Top N**                 | The best N items, without sorting everyone.                             | Keeping the 10 best cards in your hand while dealing a whole deck. | `topN`                      |
| **Priority queue (heap)** | A collection that always knows its smallest item.                       | A queue where the weakest card is always on top, ready to drop.    | `PriorityQueue`             |

# 2 · Build: Spec

## Business problem

**Shikshalab** (a fictional learning app) shows quiz leaderboards. Two students with the same score get ranks 3 and 4, and the "top 10" sometimes shows 11 names.

## Acceptance criteria

On quiz 3, "Algebra sprint": 12 students, ties at 3rd, 6th and 10th.

1.  **Given** Kabir and Meera both at 88, **then** both are rank 3 (dense 3), Kabir shown first (250 s against 310 s), and the next student is rank 5 (dense 4).
2.  **Given** `top=10` with a tie for 10th, **then** exactly 10 rows, the faster of the two shown, and `moreTiedAtCutoff: 1`.
3.  **Given** Reyansh asks for his place, **then** rank 10, dense 8, of 12, though he is not in the top 10 rows.
4.  **Given** equal score and equal time, **then** the same rank, ordered by student id, the same on every request.
5.  **Given** an unknown quiz, or a student who did not attempt it, `404`; `top` outside 1 to 100, or a missing or malformed student id, `400`.

## Requirements

- Ranks depend on the score only; time and id decide only the display order.
- Top N is at most N rows; ties beyond the cut are counted.
- Top N uses a heap of N + 1, not a sort of every attempt.
- Student ids normalised with `Locale.ROOT`.

## Learning objectives

- Tell competition from dense ranking, and compute both.
- Build a comparator chain, and know what `reversed()` applies to.
- Find the top N with a `PriorityQueue`.
- Define "top N" precisely when there are ties.

# 2 · Build: API contract

## Endpoints

| Method | Path                               | Purpose                                                             |
|--------|------------------------------------|---------------------------------------------------------------------|
| `GET`  | `/quizzes/{id}/leaderboard?top=10` | The best `top` students (1 to 100, default 10).                     |
| `GET`  | `/quizzes/{id}/leaderboard/me`     | Your own rank. Header `X-Student-Id` (demo stand-in for the login). |

## Status codes

| Status | When                                                                      |
|--------|---------------------------------------------------------------------------|
| 200    | A board, or your place                                                    |
| 400    | `top` outside 1 to 100 or not a number; a missing or malformed student id |
| 404    | No such quiz, or no attempt by that student                               |

## Captured examples

Captured with curl from the running app on 15 Oct 2026. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: the top ten of quiz 3

**Why:** ranks 3, 3 and 6, 6 shared; ten rows; one more tied at 10th.

Request

``` code
GET /quizzes/3/leaderboard HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 949

{
  "quizId": 3,
  "title": "Algebra sprint",
  "participants": 12,
  "rows": [
    {
      "rank": 1,
      "denseRank": 1,
      "studentId": "S-1001",
      "name": "Aarav",
      "score": 95,
      "seconds": 300
    },
    {
      "rank": 2,
      "denseRank": 2,
      "studentId": "S-1002",
      "name": "Diya",
      "score": 92,
      "seconds": 280
    },
    {
      "rank": 3,
      "denseRank": 3,
      "studentId": "S-1003",
      "name": "Kabir",
      "score": 88,
      "seconds": 250
    },
    {
      "rank": 3,
      "denseRank": 3,
      "studentId": "S-1004",
      "name": "Meera",
      "score": 88,
      "seconds": 310
    },
    {
      "rank": 5,
      "denseRank": 4,
      "studentId": "S-1005",
      "name": "Rohan",
      "score": 85,
      "seconds": 200
    },
    {
      "rank": 6,
      "denseRank": 5,
      "studentId": "S-1007",
      "name": "Vihaan",
      "score": 80,
      "seconds": 260
    },
    {
      "rank": 6,
      "denseRank": 5,
      "studentId": "S-1006",
      "name": "Ananya",
      "score": 80,
      "seconds": 400
    },
    {
      "rank": 8,
      "denseRank": 6,
      "studentId": "S-1008",
      "name": "Ishita",
      "score": 78,
      "seconds": 330
    },
    {
      "rank": 9,
      "denseRank": 7,
      "studentId": "S-1009",
      "name": "Arjun",
      "score": 75,
      "seconds": 290
    },
    {
      "rank": 10,
      "denseRank": 8,
      "studentId": "S-1010",
      "name": "Saanvi",
      "score": 70,
      "seconds": 240
    }
  ],
  "moreTiedAtCutoff": 1
}
```

### Case 2: the top three

**Why:** Kabir fits, Meera (also 88, slower) does not: `moreTiedAtCutoff: 1`.

Request

``` code
GET /quizzes/3/leaderboard?top=3 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 342

{
  "quizId": 3,
  "title": "Algebra sprint",
  "participants": 12,
  "rows": [
    {
      "rank": 1,
      "denseRank": 1,
      "studentId": "S-1001",
      "name": "Aarav",
      "score": 95,
      "seconds": 300
    },
    {
      "rank": 2,
      "denseRank": 2,
      "studentId": "S-1002",
      "name": "Diya",
      "score": 92,
      "seconds": 280
    },
    {
      "rank": 3,
      "denseRank": 3,
      "studentId": "S-1003",
      "name": "Kabir",
      "score": 88,
      "seconds": 250
    }
  ],
  "moreTiedAtCutoff": 1
}
```

### Case 3: Reyansh's place

**Why:** rank 10, though not in the ten rows.

Request

``` code
GET /quizzes/3/leaderboard/me HTTP/1.1
X-Student-Id: S-1011
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 117

{
  "quizId": 3,
  "studentId": "S-1011",
  "name": "Reyansh",
  "score": 70,
  "seconds": 270,
  "rank": 10,
  "denseRank": 8,
  "participants": 12
}
```

### Case 4: top five of 2,000

**Why:** the heap keeps five while reading 2,000 attempts.

Request

``` code
GET /quizzes/7/leaderboard?top=5 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 540

{
  "quizId": 7,
  "title": "Fractions practice",
  "participants": 2000,
  "rows": [
    {
      "rank": 1,
      "denseRank": 1,
      "studentId": "S-2487",
      "name": "Esha J.",
      "score": 100,
      "seconds": 161
    },
    {
      "rank": 1,
      "denseRank": 1,
      "studentId": "S-3823",
      "name": "Gauri O.",
      "score": 100,
      "seconds": 165
    },
    {
      "rank": 1,
      "denseRank": 1,
      "studentId": "S-2295",
      "name": "Inaaya X.",
      "score": 100,
      "seconds": 167
    },
    {
      "rank": 1,
      "denseRank": 1,
      "studentId": "S-2872",
      "name": "Myra Y.",
      "score": 100,
      "seconds": 173
    },
    {
      "rank": 1,
      "denseRank": 1,
      "studentId": "S-3104",
      "name": "Ojas J.",
      "score": 100,
      "seconds": 190
    }
  ],
  "moreTiedAtCutoff": 31
}
```

### Case 5: S-9999

**Why:** `404`.

Request

``` code
GET /quizzes/3/leaderboard/me HTTP/1.1
X-Student-Id: S-9999
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "S-9999 has not attempted quiz 3.",
  "instance": "/quizzes/3/leaderboard/me",
  "status": 404,
  "title": "No attempt"
}
```

### Case 6: `top=0`

**Why:** `400`.

Request

``` code
GET /quizzes/3/leaderboard?top=0 HTTP/1.1
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Validation failure",
  "instance": "/quizzes/3/leaderboard",
  "status": 400,
  "title": "Bad Request"
}
```

### Case 7: quiz 99

**Why:** `404`.

Request

``` code
GET /quizzes/99/leaderboard HTTP/1.1
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No quiz 99.",
  "instance": "/quizzes/99/leaderboard",
  "status": 404,
  "title": "Quiz not found"
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                              | What happens                            | Proved by                                                    |
|---------------------------------------------------|-----------------------------------------|--------------------------------------------------------------|
| Ties at 3rd, 6th and 10th                         | Shared competition and dense ranks      | `competitionAndDenseRanksOnTheHandCheckedQuiz`               |
| Equal score and equal time                        | Ordered by id, same rank                | `equalScoreAndEqualTimeAreOrderedByStudentIdAndShareTheRank` |
| `reversed()` on the whole chain                   | Slower first on ties: the slip to avoid | `reversingTheWholeChainWouldPutTheSlowerFirst`               |
| N = 1, 10, 100, 1,999, 2,000, 2,500               | The heap equals sorting everyone        | `theHeapGivesTheSameTopNAsSortingEveryone`                   |
| Each of the top 100 of 2,000 asks for their place | The same rank as on the board           | `myPlaceMatchesTheBoardForEveryStudent`                      |
| Ties beyond the cut on the 2,000                  | Counted exactly                         | `theCutoffCountIsEveryoneTiedWithTheLastRowWhoDidNotFit`     |
| Unknown quiz; no attempt                          | `404`                                   | `unknownQuizzesAndStudentsAre404`                            |
| `top` 0, 101, "ten"; quiz "abc"; no or bad header | `400`                                   | `badParametersAre400`                                        |

## The trap

Plausible but wrong

Ranking by list position, so tied scores get different ranks.

The first test ranks by position: Kabir and Meera, both 88, get 3 and 4. The second shows the quick fix: shared ranks, but "rank 10 or better" gives 11 names. The third shows the fix: ten rows, shared ranks, and one more tied counted. While building, each fix was undone once. Ranking by position turned 4 tests red, and a heap that keeps the worst 9. No time tie-break turned 1 red, no cutoff count 4, counting equal scores as ahead in "me" 2, and dense equal to competition ranks 2.

``` code
package com.shikshalab.leaderboard;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/** The first test written for this station: both complaints, reproduced on quiz 3, and the fix. */
class ListPositionRankTrapTest {

    @Test
    void rankingByPositionGivesEqualScoresDifferentRanks() {
        var old = OldLeaderboard.byPosition(Quizzes.ALGEBRA_SPRINT.attempts());
        assertThat(old.get(2).score()).isEqualTo(old.get(3).score()).isEqualTo(88);   // Kabir and Meera, both 88
        assertThat(old.get(2).rank()).isEqualTo(3);
        assertThat(old.get(3).rank()).isEqualTo(4);
    }

    @Test
    void theQuickFixShowsElevenNamesInTheTopTen() {
        assertThat(OldLeaderboard.quickFixTop(Quizzes.ALGEBRA_SPRINT.attempts(), 10)).hasSize(11);   // two students tied at 10th
    }

    @Test
    void theFixSharesRanksAndShowsAtMostTenCountingTheRest() {
        var board = new Leaderboard(new Quizzes()).top(3, 10);
        assertThat(board.rows()).hasSize(10);
        assertThat(board.rows().get(2).rank()).isEqualTo(board.rows().get(3).rank()).isEqualTo(3);
        assertThat(board.rows().getLast().name()).isEqualTo("Saanvi");   // 70 in 240 s, faster than Reyansh's 70 in 270 s
        assertThat(board.moreTiedAtCutoff()).isEqualTo(1);
    }
}
```

``` code
package com.shikshalab.leaderboard;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/** The leaderboard before the fix, kept only in tests: first by list position, then the quick fix. */
final class OldLeaderboard {

    record OldRow(int rank, String name, int score) {
    }

    private OldLeaderboard() {
    }

    /** Version 1: the rank is the position in the sorted list. */
    static List<OldRow> byPosition(List<Attempt> attempts) {
        List<Attempt> sorted = new ArrayList<>(attempts);
        sorted.sort(Comparator.comparingInt(Attempt::score).reversed());
        List<OldRow> rows = new ArrayList<>();
        for (int i = 0; i < sorted.size(); i++) {
            rows.add(new OldRow(i + 1, sorted.get(i).name(), sorted.get(i).score()));
        }
        return rows;
    }

    /** Version 2, the quick fix: equal scores share a rank, and "top 10" became "rank 10 or better". */
    static List<OldRow> quickFixTop(List<Attempt> attempts, int top) {
        List<OldRow> positions = byPosition(attempts);
        List<OldRow> rows = new ArrayList<>();
        for (int i = 0; i < positions.size(); i++) {
            OldRow r = positions.get(i);
            int rank = i > 0 && positions.get(i - 1).score() == r.score() ? rows.get(i - 1).rank() : i + 1;
            rows.add(new OldRow(rank, r.name(), r.score()));
        }
        return rows.stream().filter(r -> r.rank() <= top).toList();
    }
}
```

# 2 · Build: Set up & code

## Set up and run

| You need | Version                                         | Check with      |
|----------|-------------------------------------------------|-----------------|
| JDK      | 25 (recommended). JDK 21 also works, see below  | `java -version` |
| Maven    | Not needed: the project ships the Maven wrapper |                 |
| Docker   | Not needed for this station                     |                 |

**macOS / Linux**

``` code
./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all 19 tests
```

**Windows (PowerShell)**

``` code
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Move `.reversed()` in `Leaderboard.ORDER` to the end of the chain and run `RankingTest`. Read which test fails and why, then put it back.

``` code
curl "http://localhost:8080/quizzes/3/leaderboard?top=4"
curl http://localhost:8080/quizzes/3/leaderboard/me -H "X-Student-Id: S-1004"
```

## Troubleshooting

| You see                                      | Cause                                                                 | Fix                                                             |
|----------------------------------------------|-----------------------------------------------------------------------|-----------------------------------------------------------------|
| Ties in a different order on each request    | The comparator has no final key, and the source order changes.        | End the chain with a unique key, such as the student id.        |
| The top N comes back worst first             | The heap's comparator was not reversed, or the result was not sorted. | Heap with `ORDER.reversed()`; sort the kept items with `ORDER`. |
| `400` for `?top=50` after changing the limit | `@Max(100)` is on the parameter.                                      | Change the constraint, and the tests that check it.             |

## Project layout

``` tree
stations/035-quiz-leaderboard-ranking/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/shikshalab/leaderboard/
│   ├── LeaderboardController.java   ├── Leaderboard.java
│   ├── Attempt.java   ├── Quiz.java   ├── Quizzes.java   └── LeaderboardApplication.java
├── src/main/resources/application.yaml
├── src/test/java/com/shikshalab/leaderboard/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the pieces it uses.

#### `src/main/java/com/shikshalab/leaderboard/LeaderboardController.java`

Does  
Validates `top` and the student id, and returns the board or your place.

Why  
`@Min`/`@Max` on a parameter: Spring answers 400 by itself.

Without it  
Taking the student from a header in a real app: anyone could ask as anyone.

#### `src/main/java/com/shikshalab/leaderboard/Leaderboard.java`

Does  
The order, the top N, the ranks, and your place.

Why  
One comparator for the display order; ranks from the score alone; a heap of N + 1.

Without it  
Rank = position + 1, and top N = "rank N or better".

- `comparingInt(score).reversed()` reverses only the score; the time and id keys keep their natural order.
- The heap uses `ORDER.reversed()` so its head is the worst of the best, ready to drop.
- A row's rank: the previous row's rank on equal scores, its position otherwise. Correct because every higher score is already in the list.

#### `src/main/java/com/shikshalab/leaderboard/Attempt.java`

One attempt: student, score, seconds taken.

#### `src/main/java/com/shikshalab/leaderboard/Quiz.java`

A quiz and its attempts.

#### `src/main/java/com/shikshalab/leaderboard/Quizzes.java`

Quiz 3, checked by hand, and quiz 7, 2,000 seeded attempts.

#### `src/main/java/com/shikshalab/leaderboard/LeaderboardApplication.java`

Entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                       | Test class                     | Result |
|---------------|---------------------------------------------------|--------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found          | `LeaderboardContractTest` (5)  | pass   |
| Every station | Reproduce the failure before the fix              | `ListPositionRankTrapTest` (3) | pass   |
| This station  | Ranks, tie-breaks, heap against sorting, my place | `RankingTest` (11 runs)        | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 11, Failures: 0, Errors: 0, Skipped: 0 -- in com.shikshalab.leaderboard.RankingTest
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.shikshalab.leaderboard.LeaderboardContractTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.shikshalab.leaderboard.ListPositionRankTrapTest
[INFO] Tests run: 19, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/shikshalab/leaderboard/ListPositionRankTrapTest.java`

Written first: both complaints, then the fix.

#### `src/test/java/com/shikshalab/leaderboard/RankingTest.java`

Hand-checked ranks, the `reversed()` slip, the heap against a full sort, and my place against the board.

#### `src/test/java/com/shikshalab/leaderboard/LeaderboardContractTest.java`

Full responses compared strictly, and every refusal.

#### `src/test/java/com/shikshalab/leaderboard/OldLeaderboard.java`

The old code and its quick fix, kept only in tests.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/shikshalab/leaderboard/`.
2.  Run it: `./mvnw test -Dtest=AroundMeChallengeTest`. Challenge 1 does not compile until `around` exists; add an empty one and watch it fail.
3.  Change the code until it passes, then run `./mvnw test` to check the other 19 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 23 tests pass (19 station tests and 4 challenge tests).

Challenge 1 · Beginner-friendly · about 25 minutes

## Who is around me?

Add `around(quizId, studentId, k)`: up to k rows above and k below the student, in board order, with ranks from the whole board.

**Done when:** both tests in `AroundMeChallengeTest` pass.

Hints

- Rank the whole sorted board once, then take a slice around the student.
- `Math.max(0, i - k)` and `Math.min(size, i + k + 1)` keep the slice inside the list.

#### `challenge/AroundMeChallengeTest.java`

``` code
package com.shikshalab.leaderboard;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.groups.Tuple.tuple;

/**
 * Challenge 1: students far down the board want to see who is near them. Add Leaderboard.around(quizId, studentId, k):
 * up to k rows above and k rows below the student, in board order, with ranks from the whole board (not from the
 * window). Near the top or bottom, the window is just shorter.
 */
class AroundMeChallengeTest {

    static final Leaderboard BOARD = new Leaderboard(new Quizzes());

    @Test
    void twoAboveAndTwoBelowWithTheirRealRanks() {
        assertThat(BOARD.around(3, "S-1007", 2)).extracting(Leaderboard.Row::name, Leaderboard.Row::rank)
                .containsExactly(tuple("Meera", 3), tuple("Rohan", 5), tuple("Vihaan", 6), tuple("Ananya", 6), tuple("Ishita", 8));
    }

    @Test
    void atTheTopThereIsNothingAbove() {
        assertThat(BOARD.around(3, "S-1001", 2)).extracting(Leaderboard.Row::name).containsExactly("Aarav", "Diya", "Kabir");
        assertThat(BOARD.around(3, "S-1012", 1)).extracting(Leaderboard.Row::name, Leaderboard.Row::rank)
                .containsExactly(tuple("Reyansh", 10), tuple("Tara", 12));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 30 minutes

## Best of several attempts

Students may now try a quiz more than once. The board and "me" use each student's best attempt (highest score, then fastest), and participants counts students.

**Done when:** both tests in `BestAttemptChallengeTest` pass, and the station's tests still pass.

Hints

- `Collectors.toMap(Attempt::studentId, identity(), BinaryOperator.minBy(ORDER))` keeps the best per student.
- Use the same list for the board, the cutoff count and "me".

#### `challenge/BestAttemptChallengeTest.java`

``` code
package com.shikshalab.leaderboard;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.groups.Tuple.tuple;

/**
 * Challenge 2: students may now try a quiz more than once. The board and "me" use each student's best attempt
 * (highest score, then fastest), and participants counts students, not attempts.
 */
class BestAttemptChallengeTest {

    static Quizzes quizzesWith(List<Attempt> attempts) {
        return new Quizzes() {
            @Override
            Optional<Quiz> find(long id) {
                return Optional.of(new Quiz(id, "Retry quiz", 100, attempts));
            }
        };
    }

    static final List<Attempt> ATTEMPTS = List.of(
            new Attempt("S-0001", "Asha", 70, 300),
            new Attempt("S-0001", "Asha", 90, 400),
            new Attempt("S-0001", "Asha", 90, 350),
            new Attempt("S-0002", "Bilal", 80, 200),
            new Attempt("S-0003", "Chitra", 90, 500));

    @Test
    void eachStudentAppearsOnceWithTheirBestAttempt() {
        var board = new Leaderboard(quizzesWith(ATTEMPTS)).top(9, 10);
        assertThat(board.participants()).isEqualTo(3);
        assertThat(board.rows()).extracting(Leaderboard.Row::name, Leaderboard.Row::score, Leaderboard.Row::seconds, Leaderboard.Row::rank)
                .containsExactly(tuple("Asha", 90, 350, 1), tuple("Chitra", 90, 500, 1), tuple("Bilal", 80, 200, 3));
    }

    @Test
    void myPlaceUsesMyBestAttemptToo() {
        var me = new Leaderboard(quizzesWith(ATTEMPTS)).me(9, "S-0001");
        assertThat(me).extracting(Leaderboard.MyPlace::score, Leaderboard.MyPlace::seconds, Leaderboard.MyPlace::rank, Leaderboard.MyPlace::participants)
                .containsExactly(90, 350, 1, 3);
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## A live board for two lakh students

A national quiz has 2,00,000 students submitting in the same 10 minutes, and the board must update every few seconds. Compare recomputing from all attempts, keeping a sorted structure in memory, and a sorted set in a cache such as Valkey. How does each one answer "my rank" for a student at 1,50,000th place?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test on a quiz small enough to rank by hand.
2.  Decide the rules in words: what decides a rank, what decides display order, what "top N" means with ties.
3.  Write the comparator, then the heap, then the ranks.
4.  Check the heap against a full sort, and "me" against the board, on 2,000 attempts.

## Design alternatives and trade-offs

| Approach                 | What it costs                                            | Verdict          |
|--------------------------|----------------------------------------------------------|------------------|
| Heap of N + 1            | O(attempts × log N) time, memory for N.                  | Chosen           |
| Sort everyone, take N    | O(attempts × log attempts); simpler; fine at 2,000.      | Also fine here   |
| Rank = position + 1      | Ties get different ranks.                                | The trap         |
| Top N = rank N or better | More than N rows when there are ties.                    | The quick fix    |
| Time as part of the rank | No ties, but the rule must be announced before the quiz. | A product choice |

## Database design

None in this station. In SQL, `rank() over (order by score desc)` and `dense_rank() over (…)` compute both rankings, with `order by score desc, seconds, student_id limit 10` for the display order; `unique (quiz_id, student_id)` on attempts enforces one attempt each.

# 3 · Go deeper: Production

Fairness  
Whatever decides ties must be written in the quiz rules before students start. Changing it afterwards changes who "won".

Identity  
"Me" must come from the login. A header the client sets would let anyone see anyone's place.

Scale  
Recomputing per request is fine for thousands of attempts; for lakhs with frequent reads, keep a sorted structure or cache the board for a few seconds.

Children's data  
Leaderboards for minors often show first names only, or let a student hide their name; check the school's and the law's rules on children's data.

# 3 · Go deeper: Interview

## Interview takeaways

Competition vs dense ranking?

Both give equal values the same rank. Competition skips the following ranks (1, 2, 2, 4); dense does not (1, 2, 2, 3). SQL has rank() and dense_rank().

How do you find the top N of a large list efficiently?

A min-heap of size N: offer each item, poll when it exceeds N. O(n log N) time and O(N) memory, versus O(n log n) for a full sort.

What does Comparator.reversed() reverse?

The whole comparator it is called on. comparingInt(score).reversed().thenComparing(time) reverses only the score; ...thenComparing(time).reversed() reverses both.

Why end a comparator with a unique key?

Otherwise equal items keep whatever order the input had, which can change between requests, so the board flickers.

How do you compute one student's rank without sorting?

Count the students with a higher score and add one (competition); count distinct higher scores and add one (dense).

## Self-check rubric

| Area        | Meets the bar          | Above the bar                                                |
|-------------|------------------------|--------------------------------------------------------------|
| Correctness | All 19 tests pass.     | You moved `reversed()` and explained the failure.            |
| Ranking     | Ties share a rank.     | You can state what "top N" means with ties, in one sentence. |
| Algorithms  | A heap for top N.      | When a full sort is just as good.                            |
| Testing     | Hand-checked examples. | Checking two methods against each other on large data.       |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist on any ranking:

- Is a rank ever computed from a position in a list?
- What exactly does "top N" return when the Nth place is tied?
- Does the comparator end with a unique key?
- Where does `reversed()` sit in the chain, and what does it reverse?
