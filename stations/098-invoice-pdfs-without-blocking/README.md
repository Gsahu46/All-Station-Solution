# Station 098 · Invoice PDFs without blocking

Working Systems · 0–2 years · Core · B2B SaaS · Types: none

Spring Boot 4.1.1 · Java 25 · @Async with its own ThreadPoolTaskExecutor · CompletableFuture · 202 Accepted and an operation resource (Google AIP-151) · Awaitility. Needs JDK 25 (or 21, see Set up & code). No database, no Docker. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Rendering is simulated: demo invoice INV-2026-n has n pages and each page takes 130 ms of waiting; INV-2026-0013 always fails. The PDF itself is real: a minimal valid file with one line per page.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 8 tests.

# 1 · Understand

## The problem in real life

1.  **A 40-second click**

    An accountant clicks "Download PDF" on a 300-page invoice. The server makes the PDF inside the request: 40 seconds of a request thread doing nothing else.

2.  **Month end**

    Two hundred accountants do the same. Request threads run out, and the whole app stops answering. A quick fix moves the work to @Async: now every request is accepted and queued without limit, and when one render throws, its job says "running" for ever.

3.  **The fix**

    The request answers 202 with a job's address in milliseconds. A pool of two workers with a queue of twenty does the work; when both are full the API says "busy, try later". A failure ends the job as failed, with the reason.

Slow work leaves the request, but it still needs limits and a place to report failure.

## What are we building?

PDF jobs: start one, get its address, check it until it is done, then download the PDF, or read why it failed.

## An everyday analogy

A tailor's shop: you leave your cloth and get a slip with a number. Two tailors work; twenty orders can wait on the rail. When the rail is full, the shop says "come back tomorrow" instead of taking cloth it cannot sew. If the cloth tears, the slip says so.

## How it works in 4 steps

1.  **Start**: `POST` answers `202` with the job's address, at once.
2.  **Queue**: a worker takes the job, or it waits on a bounded queue; full means `503`.
3.  **Follow**: `GET` the job: pages done so far, then done with a PDF link or an error.
4.  **Download** the PDF from the link.

Check yourself: why refuse a job when the queue is full, instead of keeping it?

A job that would start in an hour helps nobody: the accountant gave up long ago, and the waiting jobs use memory. A clear "busy, try in 30 s" lets the client decide; the queue's limit is how long anyone would wait.

## What this station is not

- **No real PDF library.** A minimal PDF written by hand; rendering time is simulated.
- **One server.** Jobs live in memory (Production).
- **No sign-in.** Job ids are random UUIDs; access control is another station's topic.

## Key terms

| Term               | Simple meaning                                                      | Everyday example                                  | In this project           |
|--------------------|---------------------------------------------------------------------|---------------------------------------------------|---------------------------|
| **Request thread** | The server thread that answers one request; there are only so many. | A counter clerk.                                  | Tomcat's pool             |
| **@Async**         | Spring runs the method on another thread and returns at once.       | The clerk hands the order to the kitchen.         | `Renderer.render`         |
| **Executor**       | A pool of worker threads with a queue in front.                     | The kitchen: cooks, and a rail of waiting orders. | `pdfExecutor`             |
| **Bounded queue**  | A queue with a size limit: when full, new work is refused.          | "Kitchen full, come back in half an hour".        | 20                        |
| **202 Accepted**   | "Got it, not done yet", with where to check.                        | An order number.                                  | `Location: /pdf-jobs/...` |
| **Operation**      | A resource that describes long-running work until it is done.       | The order's status board.                         | AIP-151                   |

# 2 · Build: Spec

## Business problem

**Billora** (a fictional invoicing company): generating a 300-page invoice PDF holds a request thread for 40 seconds.

## Acceptance criteria

Demo rules: 2 workers, 20 waiting; INV-2026-n has n pages (1 to 500), 130 ms a page.

1.  **Given** an invoice, **then** `202` with `Location: /pdf-jobs/{uuid}` in milliseconds, whatever its size.
2.  **Given** a running job, **then** `GET` shows `done: false` and the pages done so far.
3.  **Given** a finished job, **then** `done: true` and either a response with the PDF's link or an error with the reason.
4.  **Given** both workers busy and 20 waiting, **then** a new job is `503` with `Retry-After`.
5.  **Given** the same invoice while its job is queued or running, **then** `200` with that job, not a second render.
6.  **Given** an unknown invoice or job, **then** `404`; a malformed id `400`; the PDF before it exists `409`.

## Requirements

- No PDF work on a request thread.
- A bounded pool and queue, owned by this feature.
- Every failure ends its job as failed; none is only logged.
- Tests never sleep for a fixed time.

## Learning objectives

- Configure `@Async` with a named, bounded executor and handle rejection.
- Return `CompletableFuture` from `@Async` and handle its failure.
- Design a `202` + operation resource API for long-running work.
- Test asynchronous code with Awaitility.

# 2 · Build: API contract

## Endpoints

| Method | Path                      | Purpose                                                          |
|--------|---------------------------|------------------------------------------------------------------|
| `POST` | `/invoices/{id}/pdf-jobs` | Start a PDF job; `202` and its Location.                         |
| `GET`  | `/pdf-jobs/{jobId}`       | The job as an operation: done, metadata, then response or error. |
| `GET`  | `/pdf-jobs/{jobId}/pdf`   | The finished PDF.                                                |

The operation's shape follows [AIP-151](https://google.aip.dev/151), Google's API design guideline for long-running operations (a guideline, not a formal standard): `name`, `done`, `metadata`, and when done exactly one of `response` or `error`.

## Status codes

| Status | When                                                                         |
|--------|------------------------------------------------------------------------------|
| 202    | Job started                                                                  |
| 200    | The same invoice's job is still queued or running (that job); a job; the PDF |
| 400    | An invoice id that is not `INV-YYYY-NNNN`; a job id that is not a UUID       |
| 404    | No such invoice or job                                                       |
| 409    | The PDF of a job that is not done, or failed                                 |
| 503    | Both workers busy and the queue full, with `Retry-After: 30`                 |

## Captured examples

Captured with curl from the running app on 23 Oct 2026, in this order, at the configured 130 ms a page. `Date`, connection and standard security headers are left out.

### Case 1: a three-page invoice

**Why:** `202` and the job's address; not done yet.

Request

``` code
POST /invoices/INV-2026-0003/pdf-jobs HTTP/1.1
```

Response

``` code
HTTP/1.1 202 
Location: /pdf-jobs/a906e0c9-fa57-4e94-9608-f39e61f2b40b
Content-Type: application/json

{
  "name": "pdf-jobs/a906e0c9-fa57-4e94-9608-f39e61f2b40b",
  "done": false,
  "metadata": {
    "invoiceId": "INV-2026-0003",
    "state": "RUNNING",
    "pagesDone": 0,
    "pagesTotal": 3,
    "createdAt": "2026-10-23T17:10:11.867963132Z"
  }
}
```

### Case 2: the same job, done

**Why:** a response with the PDF's link, size and pages.

Request

``` code
GET /pdf-jobs/a906e0c9-fa57-4e94-9608-f39e61f2b40b HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 301

{
  "name": "pdf-jobs/a906e0c9-fa57-4e94-9608-f39e61f2b40b",
  "done": true,
  "metadata": {
    "invoiceId": "INV-2026-0003",
    "state": "SUCCEEDED",
    "pagesDone": 3,
    "pagesTotal": 3,
    "createdAt": "2026-10-23T17:10:11.867963132Z"
  },
  "response": {
    "pdfUrl": "/pdf-jobs/a906e0c9-fa57-4e94-9608-f39e61f2b40b/pdf",
    "pages": 3,
    "bytes": 1188
  }
}
```

Downloading that PDF: its headers, then what poppler's `pdfinfo`, an independent PDF reader, says about the file.

``` code
Content-Disposition: attachment; filename="INV-2026-0003.pdf"
Content-Type: application/pdf
Content-Length: 1188
Pages:           3
Page size:       595 x 842 pts (A4)
PDF version:     1.4
```

Starting the 300-page invoice (about 40 s of work), timed by curl:

``` code
answered 202 in 0.006362 s
```

### Case 3: the 300-page job, two seconds later

**Why:** running, with its progress.

Request

``` code
GET /pdf-jobs/76e7f0ed-3b1e-43f3-8395-6c999b0ab821 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 205

{
  "name": "pdf-jobs/76e7f0ed-3b1e-43f3-8395-6c999b0ab821",
  "done": false,
  "metadata": {
    "invoiceId": "INV-2026-0300",
    "state": "RUNNING",
    "pagesDone": 15,
    "pagesTotal": 300,
    "createdAt": "2026-10-23T17:10:12.461026829Z"
  }
}
```

### Case 4: the same invoice again

**Why:** `200` with the same job: a double click does not start a second render.

Request

``` code
POST /invoices/INV-2026-0300/pdf-jobs HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Location: /pdf-jobs/76e7f0ed-3b1e-43f3-8395-6c999b0ab821
Content-Type: application/json

{
  "name": "pdf-jobs/76e7f0ed-3b1e-43f3-8395-6c999b0ab821",
  "done": false,
  "metadata": {
    "invoiceId": "INV-2026-0300",
    "state": "RUNNING",
    "pagesDone": 15,
    "pagesTotal": 300,
    "createdAt": "2026-10-23T17:10:12.461026829Z"
  }
}
```

### Case 5: its PDF before it is ready

**Why:** `409`.

Request

``` code
GET /pdf-jobs/76e7f0ed-3b1e-43f3-8395-6c999b0ab821/pdf HTTP/1.1
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "Not ready yet: the job is RUNNING.",
  "instance": "/pdf-jobs/76e7f0ed-3b1e-43f3-8395-6c999b0ab821/pdf",
  "status": 409,
  "title": "Conflict"
}
```

### Case 6: the damaged invoice

**Why:** accepted like any other.

Request

``` code
POST /invoices/INV-2026-0013/pdf-jobs HTTP/1.1
```

Response

``` code
HTTP/1.1 202 
Location: /pdf-jobs/53d0e12d-f404-43d0-a1b5-296d852b7665
Content-Type: application/json

{
  "name": "pdf-jobs/53d0e12d-f404-43d0-a1b5-296d852b7665",
  "done": false,
  "metadata": {
    "invoiceId": "INV-2026-0013",
    "state": "QUEUED",
    "pagesDone": 0,
    "pagesTotal": 13,
    "createdAt": "2026-10-23T17:10:14.560575814Z"
  }
}
```

### Case 7: the failed job

**Why:** done, with an error that says why: no job stays "running" for ever.

Request

``` code
GET /pdf-jobs/53d0e12d-f404-43d0-a1b5-296d852b7665 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 290

{
  "name": "pdf-jobs/53d0e12d-f404-43d0-a1b5-296d852b7665",
  "done": true,
  "metadata": {
    "invoiceId": "INV-2026-0013",
    "state": "FAILED",
    "pagesDone": 0,
    "pagesTotal": 13,
    "createdAt": "2026-10-23T17:10:14.560575814Z"
  },
  "error": {
    "code": "RENDER_FAILED",
    "message": "The logo image of INV-2026-0013 is damaged."
  }
}
```

### Case 8: no such invoice

**Why:** `404`.

Request

``` code
POST /invoices/INV-2026-0999/pdf-jobs HTTP/1.1
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No such invoice.",
  "instance": "/invoices/INV-2026-0999/pdf-jobs",
  "status": 404,
  "title": "Not Found"
}
```

### Case 9: not an invoice id

**Why:** `400`.

Request

``` code
POST /invoices/hello/pdf-jobs HTTP/1.1
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Validation failure",
  "instance": "/invoices/hello/pdf-jobs",
  "status": 400,
  "title": "Bad Request"
}
```

### Case 10: no such job

**Why:** `404`.

Request

``` code
GET /pdf-jobs/00000000-0000-0000-0000-000000000000 HTTP/1.1
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No such job.",
  "instance": "/pdf-jobs/00000000-0000-0000-0000-000000000000",
  "status": 404,
  "title": "Not Found"
}
```

### Case 11: month end, the 23rd big invoice at once

**Why:** two rendering, twenty waiting: `503` with `Retry-After`, instead of a place in a queue no one would wait in.

Request

``` code
POST /invoices/INV-2026-0322/pdf-jobs HTTP/1.1
```

Response

``` code
HTTP/1.1 503 
Retry-After: 30
Content-Type: application/problem+json

{
  "detail": "Too many PDFs are being made right now. Try again in a little while.",
  "instance": "/invoices/INV-2026-0322/pdf-jobs",
  "status": 503,
  "title": "Service Unavailable"
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                        | What happens                                                 | Proved by                                              |
|-------------------------------------------------------------|--------------------------------------------------------------|--------------------------------------------------------|
| Boot's default pool, 1,000 jobs                             | All accepted: 8 running, 992 waiting                         | `theDefaultPoolAcceptsEveryJobAndQueuesItWithoutLimit` |
| An @Async void method that throws; the API's failing render | Stays RUNNING; FAILED with the reason                        | `theOldWaySwallowsTheErrorAndTheApiReportsIt`          |
| A small invoice                                             | `202`, then a valid 3-page PDF                               | `aJobIsAcceptedAndEndsWithAPdf`                        |
| A 300-page invoice                                          | `202` in under 0.5 s; progress; `409` for the PDF until done | `theRequestReturnsAtOnceAndProgressCanBeFollowed`      |
| Unknown invoices, malformed ids, unknown jobs               | `404`, `400`                                                 | `unknownInvoicesAndJobsAre404AndBadIds400`             |
| A render that fails                                         | FAILED, the reason; no PDF; a new job next time              | `aFailedRenderIsAFailedJobWithItsReason`               |
| Workers and queue full                                      | `503` and `Retry-After`; accepted again later                | `whenBothWorkersAndTheQueueAreFullANewJobIs503`        |
| The same invoice twice                                      | The same job                                                 | `theSameInvoiceWhileItsJobRunsIsTheSameJob`            |

## The trap

Plausible but wrong

@Async on the default executor with unbounded queues and swallowed errors.

- **The default pool.** The test reads Spring Boot's own defaults for its task executor (8 threads, a queue of `Integer.MAX_VALUE`) and builds a pool like it. 1,000 jobs: all accepted, 8 running, 992 waiting in memory, none refused. At 40 s a render the last starts after about 83 minutes.
- **Swallowed errors.** An `@Async void` method sets "RUNNING", throws, and the line that would set "DONE" never runs. Spring logs the exception; the status says running for ever. The API's own failing render ends `FAILED` with the reason.

While building, each part was undone once: an unbounded queue turned 1 test red; no `@Async` 6; failures ignored 2; the failure not unwrapped 2; no check for a running job of the same invoice 1; a refused job left registered 1; a finished job left registered 1; no id pattern 1.

``` code
package com.billora.invoices;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.task.TaskExecutionProperties;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Import;
import org.springframework.scheduling.annotation.Async;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

import java.time.Duration;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CountDownLatch;

import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Written first. */
@Import(AsyncTrapTest.OldWay.class)
class AsyncTrapTest extends ApiTest {

    /** The old way: @Async void, and the job is marked done at the end. If the render throws, the end never comes. */
    @TestConfiguration
    static class OldWay {
        private final Map<String, String> status = new ConcurrentHashMap<>();

        public String status(String invoiceId) {   // a method: the bean is an @Async proxy, its fields are not the real ones
            return status.get(invoiceId);
        }

        @Async
        public void render(String invoiceId) {
            status.put(invoiceId, "RUNNING");
            if (invoiceId.equals("INV-2026-0013")) {
                throw new IllegalStateException("The logo image of INV-2026-0013 is damaged.");   // to a log line, and nowhere else
            }
            status.put(invoiceId, "DONE");
        }
    }

    @Autowired
    OldWay oldWay;

    @Test
    void theDefaultPoolAcceptsEveryJobAndQueuesItWithoutLimit() throws Exception {
        // Spring Boot's own defaults for its application task executor: 8 threads, a queue with no limit.
        TaskExecutionProperties.Pool defaults = new TaskExecutionProperties().getPool();
        assertThat(defaults.getCoreSize()).isEqualTo(8);
        assertThat(defaults.getQueueCapacity()).isEqualTo(Integer.MAX_VALUE);

        ThreadPoolTaskExecutor likeTheDefault = new ThreadPoolTaskExecutor();
        likeTheDefault.setCorePoolSize(defaults.getCoreSize());
        likeTheDefault.setQueueCapacity(defaults.getQueueCapacity());
        likeTheDefault.initialize();
        CountDownLatch rendering = new CountDownLatch(1);
        try {
            for (int i = 0; i < 1000; i++) {   // a month-end rush: 1,000 people press "Download PDF"
                likeTheDefault.execute(() -> {
                    try {
                        rendering.await();
                    } catch (InterruptedException e) {
                        Thread.currentThread().interrupt();
                    }
                });
            }
            // Nobody is told "busy": 8 render, 992 wait in memory. At 40 s a render, the last one starts after about 83 minutes.
            assertThat(likeTheDefault.getActiveCount()).isEqualTo(8);
            assertThat(likeTheDefault.getQueueSize()).isEqualTo(992);
        } finally {
            rendering.countDown();
            likeTheDefault.shutdown();
        }
    }

    @Test
    void theOldWaySwallowsTheErrorAndTheApiReportsIt() throws Exception {
        oldWay.render("INV-2026-0013");
        await().during(Duration.ofMillis(500)).atMost(Duration.ofSeconds(2)).until(() -> "RUNNING".equals(oldWay.status("INV-2026-0013")));

        var job = awaitDone(location(start("INV-2026-0013").andExpect(status().isAccepted())));
        assertThat(job.at("/metadata/state").asString()).isEqualTo("FAILED");
        assertThat(job.at("/error/message").asString()).isEqualTo("The logo image of INV-2026-0013 is damaged.");
    }
}
```

# 2 · Build: Set up & code

## Set up and run

| You need | Version                                         | Check with      |
|----------|-------------------------------------------------|-----------------|
| JDK      | 25 (recommended). JDK 21 also works, see below  | `java -version` |
| Maven    | Not needed: the project ships the Maven wrapper |                 |

**macOS / Linux**

``` code
./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all 8 tests
```

**Windows (PowerShell)**

``` code
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

``` code
curl -i -X POST http://localhost:8080/invoices/INV-2026-0120/pdf-jobs
curl http://localhost:8080/pdf-jobs/<the id from Location>      # again every few seconds
curl -o invoice.pdf http://localhost:8080/pdf-jobs/<id>/pdf      # once done
```

120 pages take about 16 s. Start 23 big ones in a loop and watch the 23rd get `503`.

## Troubleshooting

| You see                                   | Cause                                                                      | Fix                                      |
|-------------------------------------------|----------------------------------------------------------------------------|------------------------------------------|
| The POST still takes 40 s                 | The @Async method is called from its own class, so no proxy is in between. | Put it in another bean.                  |
| Jobs stay RUNNING after an error          | `@Async void`, or `thenAccept` without failure handling.                   | Return a future; use `whenComplete`.     |
| `No qualifying bean of type TaskExecutor` | `@Async("pdfExecutor")` names a pool that does not exist.                  | Define the executor bean with that name. |

## Project layout

``` tree
stations/098-invoice-pdfs-without-blocking/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/billora/invoices/
│   ├── PdfJobController.java   ├── PdfJobs.java   ├── Renderer.java
│   └── InvoicesApplication.java   └── Invoices.java
├── src/main/resources/application.yaml
├── src/test/java/com/billora/invoices/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels.

#### `src/main/java/com/billora/invoices/PdfJobController.java`

Does  
The three endpoints.

Why  
`202` and Location; `200` for a job already running; `503` with `Retry-After` when the pool refuses; `409` for a PDF that does not exist yet.

Without it  
A request thread held for 40 s; a client told nothing when the server is full.

#### `src/main/java/com/billora/invoices/PdfJobs.java`

Does  
Jobs as operations.

Why  
Registers a job, hands it to the renderer, and on completion records the PDF or the error.

Without it  
Jobs that say "running" after their render died; two renders of one invoice.

- `whenComplete`, not `thenAccept`: the second runs only on success.
- The failure arrives wrapped in a `CompletionException`; the job keeps the render's own message. Found while building.
- If the pool refuses, the job is unregistered so the invoice can be tried again.

#### `src/main/java/com/billora/invoices/Renderer.java`

Does  
The slow part, on the pdf pool.

Why  
`@Async("pdfExecutor")`, a `CompletableFuture`, progress per page, and a minimal PDF.

Without it  
Rendering on the caller's thread; failures that reach only a log.

- A separate bean: `@Async` works through a proxy, so calling it from the same class would run it on the caller's thread.

#### `src/main/java/com/billora/invoices/InvoicesApplication.java`

Does  
The pdf pool.

Why  
2 workers, a queue of 20, refuse when full, let running renders finish on shutdown.

Without it  
Boot's default: a queue without limit.

#### `src/main/java/com/billora/invoices/Invoices.java`

Simulated invoices: INV-2026-n has n pages.

#### `src/main/resources/application.yaml`

Workers, queue and the simulated speed.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                              | Test class                                                 | Result |
|---------------|------------------------------------------|------------------------------------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found | `PdfJobContractTest` (3), `FailureAndBackpressureTest` (3) | pass   |
| Every station | Reproduce the failure before the fix     | `AsyncTrapTest` (2)                                        | pass   |

Pages take 5 ms in the tests (300 pages in 1.5 s), with 2 workers and a queue of 3. Every wait is Awaitility: it checks every 20 ms and fails after a limit, so a test is as fast as the code and never flaky because a sleep was too short. To prove the old way's job stays "RUNNING", Awaitility's `during` checks it stays so for half a second.

Found while building: the test's `@Async` bean is a proxy, and reading its field through the proxy gave `null`; it is read through a method now.

## Run output

JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.billora.invoices.FailureAndBackpressureTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.billora.invoices.AsyncTrapTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.billora.invoices.PdfJobContractTest
[INFO] Tests run: 8, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/billora/invoices/AsyncTrapTest.java`

Written first: Boot's default pool, and an @Async void method that throws.

#### `src/test/java/com/billora/invoices/PdfJobContractTest.java`

A job from start to PDF; a big one followed while it runs; bad and unknown ids.

#### `src/test/java/com/billora/invoices/FailureAndBackpressureTest.java`

A failed render; a full pool; the same invoice twice.

#### `src/test/java/com/billora/invoices/ApiTest.java`

Shared setup: fast pages, a small pool, Awaitility helpers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/billora/invoices/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=RetryAfterChallengeTest`.
3.  Change the code until it passes, then run `./mvnw test` to check the other 8 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 12 tests pass (8 station tests and 4 challenge tests).

Challenge 1 · Beginner-friendly · about 20 minutes

## When to look again

While a job is not done, the `202` and every `GET` of it carry `Retry-After`: the seconds its remaining pages should take, rounded up, at least 1. A done job has none. Clients stop polling every 100 ms.

**Done when:** both tests in `RetryAfterChallengeTest` pass.

Hints

- Pages left times ms per page, from the operation's metadata and the configuration.
- One helper used by both endpoints.

#### `challenge/RetryAfterChallengeTest.java`

``` code
package com.billora.invoices;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: tell the client when to look again. While a job is not done, its answers carry Retry-After: the
 * seconds the pages left should take (rounded up, at least 1). A done job has none: there is nothing to wait for.
 */
class RetryAfterChallengeTest extends ApiTest {

    @Test
    void anUnfinishedJobSaysWhenToLookAgain() throws Exception {
        awaitIdlePool();
        var started = start("INV-2026-0300").andExpect(status().isAccepted()).andExpect(header().string("Retry-After", "2"));   // 300 x 5 ms
        String path = location(started);
        awaitDone(path);
        mvc.perform(get(path)).andExpect(status().isOk()).andExpect(header().doesNotExist("Retry-After"));
    }

    @Test
    void aSmallJobSaysOneSecond() throws Exception {
        awaitIdlePool();
        String path = location(start("INV-2026-0003").andExpect(header().string("Retry-After", "1")));
        awaitDone(path);
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 40 minutes

## Cancel a job

`POST /pdf-jobs/{jobId}:cancel`, AIP-151's custom method. A queued job is cancelled at once and never renders; a running one stops after its current page. Both end done, with the error code `CANCELLED`. A done job is `409`.

**Done when:** both tests in `CancelChallengeTest` pass.

Hints

- Threads cannot be stopped safely from outside: set a flag the renderer checks before each page.
- Spring's path patterns accept `{jobId}:cancel`: a variable followed by literal text.
- A queued job's render still runs once: it sees the flag and returns at once.

#### `challenge/CancelChallengeTest.java`

``` code
package com.billora.invoices;

import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: POST /pdf-jobs/{jobId}:cancel, AIP-151's custom method. A queued job is cancelled at once and never
 * renders; a running one stops after its current page. Either ends done, with the error code CANCELLED.
 */
class CancelChallengeTest extends ApiTest {

    @Test
    void aRunningJobStopsAfterItsCurrentPage() throws Exception {
        awaitIdlePool();
        String path = location(start("INV-2026-0300"));
        await().atMost(Duration.ofSeconds(5)).until(() -> job(path).at("/metadata/pagesDone").asInt() > 10);
        mvc.perform(post(path + ":cancel")).andExpect(status().isOk());
        var cancelled = awaitDone(path);
        assertThat(cancelled.at("/metadata/state").asString()).isEqualTo("CANCELLED");
        assertThat(cancelled.at("/error/code").asString()).isEqualTo("CANCELLED");
        assertThat(cancelled.at("/metadata/pagesDone").asInt()).isLessThan(300);
        mvc.perform(post(path + ":cancel")).andExpect(status().isConflict());   // already done
    }

    @Test
    void aQueuedJobIsCancelledAtOnceAndNeverRuns() throws Exception {
        awaitIdlePool();
        String a = location(start("INV-2026-0301"));
        String b = location(start("INV-2026-0302"));
        String queued = location(start("INV-2026-0303"));   // both workers busy: this one waits
        mvc.perform(post(queued + ":cancel")).andExpect(status().isOk()).andExpect(jsonPath("$.done").value(true))
                .andExpect(jsonPath("$.metadata.state").value("CANCELLED"));
        awaitDone(a);
        awaitDone(b);
        awaitIdlePool();
        assertThat(job(queued).at("/metadata/pagesDone").asInt()).isZero();
        mvc.perform(post("/pdf-jobs/" + UUID.randomUUID() + ":cancel")).andExpect(status().isNotFound());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Jobs that survive a restart

Billora runs four servers and deploys twice a day. A job started on server 2 must be readable from server 3, and a render cut off by a deploy must not be lost. Design it: a jobs table, a queue (a table with SKIP LOCKED, or a broker), PDFs in object storage with a time-limited link, and what happens to a render that was half done when its server stopped.

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: Boot's default pool, and an @Async void method that throws.
2.  Define a named, bounded executor, and a renderer bean that returns a future.
3.  Wrap the work in an operation resource: register, follow, finish.
4.  Map a refused job to `503`, and test it all with Awaitility.

## Design alternatives and trade-offs

| Approach                                 | What it costs                                                             | Verdict             |
|------------------------------------------|---------------------------------------------------------------------------|---------------------|
| A bounded executor, 202 and an operation | Clients poll; jobs need a home.                                           | Chosen              |
| Make the PDF inside the request          | A request thread per render; time limits on the way.                      | The problem         |
| @Async on Boot's default pool, void      | Unbounded queue; errors only logged.                                      | The trap            |
| Virtual threads for renders              | No thread shortage, but no limit either: CPU and memory become the limit. | Still needs a limit |
| A message queue and worker service       | More parts; survives restarts and scales on its own.                      | At larger scale     |

## Database design

No database: jobs are in memory, which loses them on restart and hides them from other servers (challenge 3).

# 3 · Go deeper: Production

Sizing  
Workers are limited by CPU and memory per render; the queue by how long a user will wait (20 jobs × 40 s / 2 workers ≈ 7 minutes here).

Shutdown  
The pool waits up to 60 s for running renders on shutdown; longer jobs need to be resumable (challenge 3).

Clean-up  
Finished jobs and their PDFs are never removed here. Expire them (an hour, a day) and say so in the API.

Monitoring  
Watch queue length, active workers, rejections and failures: `ThreadPoolTaskExecutor` exposes them, and Micrometer can publish them.

Push instead of poll  
Email or a webhook when done saves clients from polling; `Retry-After` (challenge 1) makes polling cheaper.

# 3 · Go deeper: Interview

## Interview takeaways

How do you keep a slow task off the request thread?

Run it on a separate, bounded executor; answer 202 with a status URL.

What is wrong with Spring Boot's default @Async pool for this?

Its queue has no limit: it accepts everything, runs out of memory or makes users wait for hours, and nobody is told "busy".

What happens to an exception in an @Async void method?

It goes to the AsyncUncaughtExceptionHandler, which logs it. The caller never knows. Return a CompletableFuture instead.

Why does @Async sometimes not work?

It is applied by a proxy: calling the method from the same class bypasses it.

How do you test async code?

Wait for the condition with Awaitility (poll until true, with a limit), never a fixed sleep.

What does a client get when the server is full?

503 with Retry-After: an honest answer it can act on.

## Self-check rubric

| Area        | Meets the bar                | Above the bar                                           |
|-------------|------------------------------|---------------------------------------------------------|
| Correctness | All 8 tests pass.            | You ran the flawed version and explained each failure.  |
| Async       | @Async with a named pool.    | Bounded, rejection mapped to 503, failures recorded.    |
| API         | 202 and a status URL.        | An operation shape with progress, response or error.    |
| Testing     | Awaitility instead of sleep. | A test that proves the request returns before the work. |

# 3 · Go deeper: Review

## The pull request

A teammate tidies up: the custom executor goes ("Boot already has one"), `@Async` loses its name, and `whenComplete` becomes `thenAccept` ("we only need the PDF"). Read the three files and list every problem before opening the findings.

#### `review/InvoicesApplication.java`

``` code
package com.billora.invoices;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableAsync;

@SpringBootApplication
@EnableAsync
public class InvoicesApplication {

    public static void main(String[] args) {
        SpringApplication.run(InvoicesApplication.class, args);
    }

    // Spring Boot already configures a task executor for @Async: no need for our own.
}
```

#### `review/Renderer.java (only the annotation differs)`

``` code
 * Renders an invoice as a PDF on the pdf pool. A separate bean on purpose: @Async works through a proxy, so a call
    @Async
    CompletableFuture<byte[]> render(PdfJobs.Job job) {
```

#### `review/PdfJobs.java`

``` code
package com.billora.invoices;

import com.fasterxml.jackson.annotation.JsonInclude;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.task.TaskRejectedException;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.CompletionException;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Long-running work as an operation resource, in the shape of Google's AIP-151 (an API design guideline, not a
 * formal standard): a name, done, metadata while it runs, then a response or an error.
 * shortcut: jobs and finished PDFs are kept in this server's memory and never removed; store PDFs in object storage
 * and the jobs in a database, and expire them, before running more than one server.
 */
@Service
class PdfJobs {

    enum State { QUEUED, RUNNING, SUCCEEDED, FAILED }

    static final class Job {
        private final UUID id = UUID.randomUUID();
        private final Invoices.Invoice invoice;
        private final Instant createdAt = Instant.now();
        private final AtomicInteger pagesDone = new AtomicInteger();
        private volatile State state = State.QUEUED;
        private volatile byte[] pdf;
        private volatile String error;

        Job(Invoices.Invoice invoice) {
            this.invoice = invoice;
        }

        Invoices.Invoice invoice() {
            return invoice;
        }

        void started() {
            state = State.RUNNING;
        }

        void pageDone() {
            pagesDone.incrementAndGet();
        }
    }

    @JsonInclude(JsonInclude.Include.NON_NULL)
    record Operation(String name, boolean done, Metadata metadata, Result response, Error error) {
    }

    record Metadata(String invoiceId, State state, int pagesDone, int pagesTotal, Instant createdAt) {
    }

    record Result(String pdfUrl, int pages, int bytes) {
    }

    record Error(String code, String message) {
    }

    record Submitted(Operation operation, boolean existing) {
    }

    private static final Logger log = LoggerFactory.getLogger(PdfJobs.class);
    private final Map<UUID, Job> jobs = new ConcurrentHashMap<>();
    private final Map<String, Job> activeByInvoice = new ConcurrentHashMap<>();
    private final Renderer renderer;

    PdfJobs(Renderer renderer) {
        this.renderer = renderer;
    }

    /**
     * Queues a render and returns at once. The same invoice while its job is queued or running gets that job back.
     * Throws TaskRejectedException when the pool and its queue are full.
     */
    Submitted submit(Invoices.Invoice invoice) {
        Job fresh = new Job(invoice);
        Job active = activeByInvoice.putIfAbsent(invoice.id(), fresh);
        if (active != null) {
            return new Submitted(view(active), true);
        }
        try {
            renderer.render(fresh).thenAccept(pdf -> finish(fresh, pdf, null));   // simpler: we only need the PDF
        } catch (TaskRejectedException full) {
            activeByInvoice.remove(invoice.id(), fresh);
            throw full;
        }
        jobs.put(fresh.id, fresh);
        return new Submitted(view(fresh), false);
    }

    private void finish(Job job, byte[] pdf, Throwable failure) {
        if (failure != null) {
            // The future's stages wrap what the render threw: report the render's own message.
            Throwable cause = failure instanceof CompletionException && failure.getCause() != null ? failure.getCause() : failure;
            log.warn("PDF job {} for {} failed", job.id, job.invoice.id(), cause);   // logged and kept on the job
            job.error = cause.getMessage();
            job.state = State.FAILED;
        } else {
            job.pdf = pdf;
            job.state = State.SUCCEEDED;
        }
        activeByInvoice.remove(job.invoice.id(), job);
    }

    Optional<Operation> find(UUID id) {
        return Optional.ofNullable(jobs.get(id)).map(PdfJobs::view);
    }

    /** The PDF of a finished job; empty if there is no such job or it has not succeeded. */
    Optional<byte[]> pdf(UUID id) {
        return Optional.ofNullable(jobs.get(id)).map(j -> j.pdf);
    }

    private static Operation view(Job j) {
        State state = j.state;
        Metadata metadata = new Metadata(j.invoice.id(), state, j.pagesDone.get(), j.invoice.pages(), j.createdAt);
        return switch (state) {
            case SUCCEEDED -> new Operation(name(j), true, metadata, new Result("/pdf-jobs/" + j.id + "/pdf", j.invoice.pages(), j.pdf.length), null);
            case FAILED -> new Operation(name(j), true, metadata, null, new Error("RENDER_FAILED", j.error));
            default -> new Operation(name(j), false, metadata, null, null);
        };
    }

    private static String name(Job j) {
        return "pdf-jobs/" + j.id;
    }
}
```

## Findings

1Boot's default executor queues without limit

"Spring Boot already configures a task executor": 8 threads and a queue of `Integer.MAX_VALUE`. At month end every job is accepted, the queue grows in memory, and users wait for hours with no "busy". `@Async` without a name also shares that pool with every other async task in the app.

**Test evidence:** `whenBothWorkersAndTheQueueAreFullANewJobIs503` fails: the 6th job is accepted.

2thenAccept only runs on success

"Simpler: we only need the PDF": when the render throws, `thenAccept` is skipped, the failure goes nowhere, and the job says RUNNING for ever. The trap's swallowed error, moved one line.

**Test evidence:** `aFailedRenderIsAFailedJobWithItsReason` and `theOldWaySwallowsTheErrorAndTheApiReportsIt` fail: the job never finishes.

## Same tests, flawed version

From `docs/review-run.txt`: the flawed files copied over the real ones, then the full suite run.

| Test class                   | Fixed version | Flawed version |
|------------------------------|---------------|----------------|
| `PdfJobContractTest`         | 3 / 3         | 3 / 3          |
| `AsyncTrapTest`              | 2 / 2         | 1 / 2          |
| `FailureAndBackpressureTest` | 3 / 3         | 1 / 3          |

On a quiet day with good invoices, the flawed version works and the PDFs arrive. It fails on the days that matter: month end, and the invoice with a broken logo.
