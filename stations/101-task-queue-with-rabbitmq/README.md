# Station 101 · Task queue with RabbitMQ

Working Systems · 0–2 years · Core · Healthcare · Types: Messaging, Idempotency

Spring Boot 4.1.1 · Java 25 · RabbitMQ 4.1 · Spring AMQP 4.1 (@RabbitListener, publisher confirms, retry, dead-letter exchange) · Testcontainers · Awaitility. Needs JDK 25 (or 21, see Set up & code) and Docker running (RabbitMQ for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** The lab is simulated: report LR-n has n pages, each taking a few milliseconds; LR-0013 always fails and LR-0042 fails once. The PDFs are real minimal files, kept on the local disk instead of object storage.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 12 tests.

# 1 · Understand

## The problem in real life

1.  **Reports in the request**

    At Mediqo, the doctor's "get report" click made the PDF in the request itself. At peak, requests waited; a server restart in the middle lost the reports being made.

2.  **A queue that forgets**

    A queue fixed the waiting. But the workers used auto-ack: RabbitMQ treated a report as done the moment it handed it to a worker. A worker that restarted mid-report took that report with it.

3.  **The fix**

    The broker confirms each message before the API says "accepted". A worker acknowledges only after the PDF is saved; if it dies, the broker gives the report to another worker. Reports that fail three times wait in a dead-letter queue with the reason.

A message is safe only until someone says it is done. Say it after the work, never before.

## What are we building?

A render queue for lab reports: the API puts a request on a durable queue, workers turn it into a PDF, and nothing is lost when a worker dies.

## An everyday analogy

A courier signs for a parcel only when it is in the customer's hands. If the courier's van breaks down, the depot still has the parcel on its books and sends another courier. Parcels that cannot be delivered after three tries go to the returns office with a note.

## How it works in 4 steps

1.  **Send**: the API publishes the request and waits for the broker's confirmation, then answers `202`.
2.  **Take**: a worker takes one message at a time (prefetch 1).
3.  **Finish**: the worker saves the PDF; only then is the message acknowledged and deleted.
4.  **Give up well**: after three failed tries, the message goes to the dead-letter queue and the report shows why.

Check yourself: the worker saves the PDF, then dies before acknowledging. What happens?

The broker gives the message to another worker, marked as redelivered. That worker finds the PDF already there and skips it. Delivery is at least once, so workers must be safe to repeat.

## What this station is not

- **No real lab system.** Rendering is simulated; the PDFs are minimal.
- **One machine's disk.** Reports would go to object storage with several servers.
- **No sign-in.** Access control is another station's topic.

## Key terms

| Term                         | Simple meaning                                                           | Everyday example                     | In this project            |
|------------------------------|--------------------------------------------------------------------------|--------------------------------------|----------------------------|
| **Message broker**           | A server that holds messages until a worker takes them.                  | A post office.                       | RabbitMQ                   |
| **Exchange and routing key** | Where a message is sent, and the label that decides which queue gets it. | The sorting desk and the PIN code.   | `lab-reports`, `render`    |
| **Queue**                    | Messages waiting, in order, for a worker.                                | A pile of letters for one postman.   | `report-render`            |
| **Acknowledgement**          | The worker telling the broker "done, you can delete it".                 | The signature on a delivery slip.    | after the listener returns |
| **Prefetch**                 | How many messages a worker may hold at once before acknowledging.        | Letters a postman carries per round. | 1                          |
| **Dead-letter queue**        | Where messages go that no worker could handle, for a person.             | The returned-letters office.         | `report-render.dlq`        |

# 2 · Build: Spec

## Business problem

**Mediqo** (a fictional diagnostics lab): lab report PDFs are generated in the request thread; at peak, reports are lost when a server restarts.

## Acceptance criteria

Demo rules: reports LR-0001 to LR-0500; 3 tries, 1 s then 2 s apart; one report per worker at a time; two workers.

1.  **Given** a known report, **then** `202` only after the broker has confirmed the message, and later `READY` with a PDF.
2.  **Given** the broker unreachable or refusing the message, **then** `503`, and asking again tries again.
3.  **Given** the same report asked for again, **then** `200` with its state and no second render.
4.  **Given** a worker that dies mid-report, **then** another worker renders it; nothing is lost.
5.  **Given** a passing failure, **then** a retry renders it; a lasting one ends `FAILED` with the reason, its message in the dead-letter queue.
6.  **Given** a slow report, **then** the reports after it go to the other worker.

## Requirements

- Durable queues and persistent messages.
- Acknowledge after the work, not before.
- Every message ends rendered, or parked with a reason: never silently gone, never retried for ever.

## Learning objectives

- Declare exchanges, queues, bindings and a dead-letter exchange.
- Choose acknowledgement mode and prefetch, and explain Spring's "auto" against RabbitMQ's autoAck.
- Use publisher confirms, listener retry and a message recoverer.
- Make a consumer idempotent, and test crashes against a real broker.

# 2 · Build: API contract

## Endpoints

| Method | Path                       | Purpose                                                          |
|--------|----------------------------|------------------------------------------------------------------|
| `POST` | `/lab-reports/{id}/render` | Queue a render; `202` once the broker has it.                    |
| `GET`  | `/lab-reports/{id}`        | QUEUED, READY (with the PDF's link) or FAILED (with the reason). |
| `GET`  | `/lab-reports/{id}/pdf`    | The PDF.                                                         |
| worker | queue `report-render`      | Renders; acknowledges after the PDF is saved.                    |

## Status codes

| Status | When                                             |
|--------|--------------------------------------------------|
| 202    | Render queued and confirmed by the broker        |
| 200    | Asked again: its state, nothing new sent; a read |
| 400    | Not a report id (LR-0000 form)                   |
| 404    | No such report; never requested; no PDF yet      |
| 503    | The broker is unreachable or refused the message |

## Captured examples

Captured with curl from the running app on 24 Oct 2026, in this order, with the configured retry waits (1 s, 2 s). `Date`, connection and standard security headers are left out.

### Case 1: render LR-0007

**Why:** `202` after the broker's confirmation.

Request

``` code
POST /lab-reports/LR-0007/render HTTP/1.1
```

Response

``` code
HTTP/1.1 202 
Location: /lab-reports/LR-0007
Content-Type: application/json

{
  "reportId": "LR-0007",
  "status": "QUEUED"
}
```

### Case 2: a moment later

**Why:** a worker rendered it.

Request

``` code
GET /lab-reports/LR-0007 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 75

{
  "reportId": "LR-0007",
  "status": "READY",
  "pdfUrl": "/lab-reports/LR-0007/pdf"
}
```

The PDF, read by poppler's `pdfinfo`, an independent reader:

``` code
Pages:           7
Page size:       595 x 842 pts (A4)
PDF version:     1.4
```

### Case 3: asked again

**Why:** `200`, ready: no second message.

Request

``` code
POST /lab-reports/LR-0007/render HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json

{
  "reportId": "LR-0007",
  "status": "READY",
  "pdfUrl": "/lab-reports/LR-0007/pdf"
}
```

### Case 4: LR-0042, whose lab system is busy once

**Why:** accepted like any other.

Request

``` code
POST /lab-reports/LR-0042/render HTTP/1.1
```

Response

``` code
HTTP/1.1 202 
Location: /lab-reports/LR-0042
Content-Type: application/json

{
  "reportId": "LR-0042",
  "status": "QUEUED"
}
```

### Case 5: ready after a retry

**Why:** the first try failed; the second, 1 s later, worked.

Request

``` code
GET /lab-reports/LR-0042 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 75

{
  "reportId": "LR-0042",
  "status": "READY",
  "pdfUrl": "/lab-reports/LR-0042/pdf"
}
```

### Case 6: LR-0013, a damaged scan

**Why:** accepted; the worker will fail.

Request

``` code
POST /lab-reports/LR-0013/render HTTP/1.1
```

Response

``` code
HTTP/1.1 202 
Location: /lab-reports/LR-0013
Content-Type: application/json

{
  "reportId": "LR-0013",
  "status": "QUEUED"
}
```

### Case 7: failed after three tries

**Why:** the reason, recorded by the recoverer before it dead-lettered the message.

Request

``` code
GET /lab-reports/LR-0013 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 84

{
  "reportId": "LR-0013",
  "status": "FAILED",
  "failure": "The scan of LR-0013 is damaged."
}
```

The parked message, read through the management API without taking it off the dead-letter queue. `x-death` is written by the broker:

``` code
payload: {"reportId":"LR-0013"}
x-death: {'reason': 'rejected', 'queue': 'report-render', 'exchange': 'lab-reports', 'count': 1}
```

### Case 8: no such report

**Why:** `404`, nothing sent.

Request

``` code
POST /lab-reports/LR-0999/render HTTP/1.1
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No such report.",
  "instance": "/lab-reports/LR-0999/render",
  "status": 404,
  "title": "Not Found"
}
```

### Case 9: not a report id

**Why:** `400`.

Request

``` code
POST /lab-reports/report-7/render HTTP/1.1
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "A report id looks like LR-0042.",
  "instance": "/lab-reports/report-7/render",
  "status": 400,
  "title": "Bad Request"
}
```

## The queues

At the end, from `rabbitmqctl list_queues` (the management API's counts can be a few seconds old):

``` code
name  messages_ready  messages_unacknowledged consumers
report-render   0   0   2
report-render.dlq   1   0   0
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                              | What happens                                       | Proved by                                                         |
|---------------------------------------------------|----------------------------------------------------|-------------------------------------------------------------------|
| Auto-ack, the worker dies before rendering        | The queue is empty: the report is gone             | `withAutoAckTheMessageIsGoneWithTheWorker`                        |
| Acknowledge after the work, the same death        | The message is back, flagged redelivered           | `withAcknowledgementsAfterTheWorkTheBrokerGivesItToTheNextWorker` |
| A report                                          | `202`, then READY and a 7-page PDF                 | `aReportIsQueuedThenRenderedByAWorker`                            |
| Unknown, bad ids, never requested                 | `404`, `400`, nothing sent                         | `unknownReportsAre404AndBadIds400`                                |
| A slow report first, two quick ones after         | The quick ones are done while the slow one renders | `aSlowReportDoesNotHoldUpTheOnesBehindIt`                         |
| The broker refuses the message (exchange missing) | `503`, then fine once it is back                   | `aMessageTheBrokerDidNotTakeIs503`                                |
| No broker at all                                  | `503`, twice: nothing marked as queued             | `withoutTheBrokerItIs503AndTheRequestCanBeTriedAgain`             |
| A failure that passes                             | Retried, rendered once, nothing parked             | `aBusyLabSystemIsRetriedAndTheReportIsRendered`                   |
| A failure that lasts                              | FAILED with the reason; parked with `x-death`      | `aDamagedReportEndsInTheDeadLetterQueueWithItsReason`             |
| The worker's connection cut mid-render            | Redelivered; rendered once by the next worker      | `aWorkerCutOffMidRenderLosesNothing`                              |
| The same request twice                            | One message, one render                            | `theSameRequestTwiceIsOneMessageAndOneRender`                     |
| A repeated message for a rendered report          | Acknowledged and skipped                           | `aRepeatedMessageForARenderedReportIsSkipped`                     |

## The trap

Plausible but wrong

Auto-ack, so messages are lost when a worker crashes.

- **Auto-ack.** With the plain RabbitMQ client: a worker consumes with `autoAck=true`, takes the message, and its channel closes before it renders. The queue is empty. The report will never be made, and nothing records that.
- **Acknowledge after the work.** The same death with `autoAck=false`: the message is back in the queue, and the next worker sees it marked redelivered.
- **The app.** Spring's `acknowledge-mode: auto` acknowledges after the listener returns. In `aWorkerCutOffMidRenderLosesNothing` the broker closes the app's connection in the middle of a 500-page report: the report is still rendered, once.

While building, each part was undone once: `acknowledge-mode: none` turned 2 tests red; no retry 2; prefetch 250 1; no dead-letter exchange 1; no recoverer 1; no skip of rendered reports 1; no "requested" marker 1; no wait for the broker's confirmation 1; the marker kept after a refused publish 2. Two parts turned nothing red and stay, with their reasons: writing the PDF next to its name and moving it (so nobody reads half a PDF, which no test catches), and the worker stopping when its channel closes (see Tests).

``` code
package com.mediqo.reports;

import com.rabbitmq.client.Channel;
import com.rabbitmq.client.Connection;
import com.rabbitmq.client.ConnectionFactory;
import com.rabbitmq.client.GetResponse;
import org.junit.jupiter.api.Test;

import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;

import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;

/**
 * A worker takes a render request and its server restarts before the PDF is made. Written first, with the plain
 * RabbitMQ client so nothing hides what the broker does.
 */
class AutoAckTrapTest extends ApiTest {

    Connection connect() throws Exception {
        ConnectionFactory factory = new ConnectionFactory();
        factory.setHost(rabbit.getHost());
        factory.setPort(rabbit.getAmqpPort());
        return factory.newConnection();
    }

    /** One worker takes the message, then dies (its channel closes) without rendering. What is left in the queue? */
    long leftAfterAWorkerDies(String queue, boolean autoAck) throws Exception {
        try (Connection connection = connect()) {
            Channel setup = connection.createChannel();
            setup.queueDeclare(queue, false, false, false, null);
            setup.basicPublish("", queue, null, "{\"reportId\":\"LR-0007\"}".getBytes(StandardCharsets.UTF_8));
            Channel worker = connection.createChannel();
            List<String> taken = new CopyOnWriteArrayList<>();
            worker.basicConsume(queue, autoAck, (tag, delivery) -> taken.add(new String(delivery.getBody(), StandardCharsets.UTF_8)), tag -> {
            });
            await().atMost(Duration.ofSeconds(5)).until(() -> taken.size() == 1);
            worker.close();   // the server restarts: no render, no acknowledgement
            await().atMost(Duration.ofSeconds(5)).until(() -> setup.messageCount(queue) == (autoAck ? 0 : 1));
            if (!autoAck) {
                GetResponse again = setup.basicGet(queue, true);
                assertThat(again.getEnvelope().isRedeliver()).isTrue();   // the next worker is told it may be a repeat
            }
            long left = autoAck ? setup.messageCount(queue) : 1;
            setup.queueDelete(queue);
            return left;
        }
    }

    @Test
    void withAutoAckTheMessageIsGoneWithTheWorker() throws Exception {
        assertThat(leftAfterAWorkerDies("trap.auto-ack", true)).isZero();   // the report is never rendered, and nothing says so
    }

    @Test
    void withAcknowledgementsAfterTheWorkTheBrokerGivesItToTheNextWorker() throws Exception {
        assertThat(leftAfterAWorkerDies("trap.manual-ack", false)).isEqualTo(1);
    }
}
```

# 2 · Build: Set up & code

## Set up and run

| You need | Version                                                           | Check with      |
|----------|-------------------------------------------------------------------|-----------------|
| JDK      | 25 (recommended). JDK 21 also works, see below                    | `java -version` |
| Docker   | Docker Desktop (Windows, macOS) or Docker Engine (Linux), running | `docker info`   |
| Maven    | Not needed: the project ships the Maven wrapper                   |                 |

**macOS / Linux**

``` code
docker compose up -d        # RabbitMQ on localhost:5672, management UI on http://localhost:15672
./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all 12 tests; starts its own RabbitMQ container
```

**Windows (PowerShell)**

``` code
docker compose up -d
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Queue a long report and stop the app while it renders:

``` code
curl -X POST http://localhost:8080/lab-reports/LR-0500/render
# within 10 s: stop the app (Ctrl+C), then start it again
curl http://localhost:8080/lab-reports/LR-0500
```

The report is rendered after the restart: the broker kept the unacknowledged message. Open the management UI and watch *Unacked* go to 1 and back.

## Troubleshooting

| You see                                     | Cause                                                                                 | Fix                                                                  |
|---------------------------------------------|---------------------------------------------------------------------------------------|----------------------------------------------------------------------|
| `PRECONDITION_FAILED - inequivalent arg`    | The queue exists with other arguments (for example without the dead-letter exchange). | Delete it, or declare a new queue; arguments cannot change in place. |
| Messages pile up as Unacked                 | A worker is stuck, or prefetch is high and one worker hoards them.                    | Prefetch 1 for long tasks; look at the worker.                       |
| `Could not find a valid Docker environment` | Docker is not running.                                                                | Start Docker Desktop or the Docker service.                          |

## Project layout

``` tree
stations/101-task-queue-with-rabbitmq/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/mediqo/reports/
│   ├── ReportController.java   ├── ReportsApplication.java   ├── RenderWorker.java
│   └── GiveUp.java   ├── LabReports.java   └── Pdf.java
├── src/main/resources/application.yaml
├── src/test/java/com/mediqo/reports/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the worker and what happens when it gives up.

#### `src/main/java/com/mediqo/reports/ReportController.java`

Does  
The API.

Why  
Checks the id, marks the report requested (once), publishes and waits for the broker's confirmation; reads state from the report files.

Without it  
A `202` for a message the broker never got; two messages for one report.

- A refused confirmation arrives as the RabbitMQ client's `ShutdownSignalException`, not Spring's `AmqpException`: both are caught. Found while building.
- If publishing fails, the marker is removed so the next request tries again.

#### `src/main/java/com/mediqo/reports/ReportsApplication.java`

Does  
The topology.

Why  
A direct exchange, the durable work queue with its dead-letter exchange, and the dead-letter queue; JSON messages.

Without it  
Messages lost with a restart of the broker, or dropped when rejected.

#### `src/main/java/com/mediqo/reports/RenderWorker.java`

Does  
The worker.

Why  
Skips reports already rendered, renders page by page, saves the PDF; returns normally only when done.

Without it  
Lost or doubled reports when workers die or messages repeat.

- If its channel is closed mid-render, the broker has already given the message to another worker: it stops instead of racing it.
- The two simulated failures: LR-0013 always, LR-0042 once.

#### `src/main/java/com/mediqo/reports/GiveUp.java`

Does  
After the last retry.

Why  
Writes the reason on the report, then rejects without requeue: the broker dead-letters it.

Without it  
A report that fails silently, or a message retried for ever.

#### `src/main/java/com/mediqo/reports/LabReports.java`

Does  
Reports on disk.

Why  
An atomic "requested" marker, the PDF written then moved, the failure note; ids checked before any file is touched.

Without it  
Half-written PDFs; paths built from user input.

#### `src/main/java/com/mediqo/reports/Pdf.java`

A minimal valid PDF, one line per page.

#### `src/main/resources/application.yaml`

Publisher confirms, `acknowledge-mode: auto`, prefetch 1, two consumers, retry.

#### `compose.yaml`

RabbitMQ 4.1 with the management UI on port 15672 (guest / guest).

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                     | Test class                                     | Result |
|---------------|-------------------------------------------------|------------------------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found        | `RenderContractTest` (4), `BrokerDownTest` (1) | pass   |
| Every station | Reproduce the failure before the fix            | `AutoAckTrapTest` (2)                          | pass   |
| Messaging     | Duplicate delivery, retry and dead letter       | `RetryAndDeadLetterMessagingTest` (3)          | pass   |
| Idempotency   | Replay: the same request twice gives one effect | `DuplicateRenderReplayTest` (2)                | pass   |

A real RabbitMQ in Docker. To kill a worker the way a crash does, a test closes the app's connection from the broker's side through the management API; the broker puts the unacknowledged message back.

Found while building, twice over: the first version of that test passed and proved nothing. The management API lists connections a few seconds late, so the test closed no connection at all; and once it did, a worker that had lost its connection kept rendering and saved the PDF anyway, so even `acknowledge-mode: none` passed. Now the test finds the app's connection before it starts, and the worker stops when its channel closes, as a crashed one would: with `none` the report is lost and the test fails.

## Run output

JDK 25.0.1, Spring Boot 4.1.1, RabbitMQ 4.1 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.mediqo.reports.RetryAndDeadLetterMessagingTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.mediqo.reports.DuplicateRenderReplayTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.mediqo.reports.AutoAckTrapTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.mediqo.reports.RenderContractTest
[INFO] Tests run: 1, Failures: 0, Errors: 0, Skipped: 0 -- in com.mediqo.reports.BrokerDownTest
[INFO] Tests run: 12, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/mediqo/reports/AutoAckTrapTest.java`

Written first: auto-ack against acknowledging after the work, with the plain client.

#### `src/test/java/com/mediqo/reports/RenderContractTest.java`

A report from request to PDF; bad and unknown ids; prefetch; a refused publish.

#### `src/test/java/com/mediqo/reports/BrokerDownTest.java`

No broker: `503`, and the next request tries again.

#### `src/test/java/com/mediqo/reports/RetryAndDeadLetterMessagingTest.java`

A retry that works; the dead-letter queue; a worker cut off mid-render.

#### `src/test/java/com/mediqo/reports/DuplicateRenderReplayTest.java`

The same request twice; a repeated message.

#### `src/test/java/com/mediqo/reports/ApiTest.java`

Shared setup: empty queues and no report files before each test.

#### `src/test/java/com/mediqo/reports/RabbitTestConfig.java`

RabbitMQ 4.1 with management, via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/mediqo/reports/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=ReplayDeadLettersChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 12 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 15 tests pass (12 station tests and 3 challenge tests).

Challenge 1 · Beginner-friendly · about 30 minutes

## Send the dead letters back

`POST /dead-letters/replay` moves every parked message back to the work queue (after someone fixed the cause) and answers how many it moved; each report goes back to QUEUED. One surprise, found while building: RabbitMQ 4 starts `x-death` afresh for a message a client publishes again, so the broker does not count the rounds for you.

**Done when:** both tests in `ReplayDeadLettersChallengeTest` pass.

Hints

- `basicGet` without auto-ack, publish it again, then acknowledge: a crash in between repeats it rather than losing it.
- Keep the message's properties when you publish it again; add your own header if you need to count replays.

#### `challenge/ReplayDeadLettersChallengeTest.java`

``` code
package com.mediqo.reports;

import org.junit.jupiter.api.Test;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.beans.factory.annotation.Autowired;

import java.time.Duration;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: POST /dead-letters/replay moves every parked message back to the work queue (after someone fixed the
 * cause) and answers how many it moved. The report goes back to QUEUED. Here the scan is still damaged, so it fails
 * again and is parked again.
 */
class ReplayDeadLettersChallengeTest extends ApiTest {

    @Autowired
    RabbitTemplate template;

    @Test
    void parkedMessagesGoBackToTheWorkQueue() throws Exception {
        render("LR-0013").andExpect(status().isAccepted());
        awaitStatus("LR-0013", "FAILED");
        await().atMost(Duration.ofSeconds(5)).until(() -> waiting(ReportsApplication.DEAD_LETTER_QUEUE) == 1);

        mvc.perform(post("/dead-letters/replay")).andExpect(status().isOk()).andExpect(jsonPath("$.moved").value(1));
        assertThat(waiting(ReportsApplication.DEAD_LETTER_QUEUE)).isZero();

        awaitStatus("LR-0013", "FAILED");   // failed again, after three more tries
        await().atMost(Duration.ofSeconds(5)).until(() -> waiting(ReportsApplication.DEAD_LETTER_QUEUE) == 1);
        Message parked = template.receive(ReportsApplication.DEAD_LETTER_QUEUE, 1_000);
        @SuppressWarnings("unchecked")
        Map<String, Object> death = ((List<Map<String, Object>>) parked.getMessageProperties().getHeaders().get("x-death")).getFirst();
        // RabbitMQ 4 does not take x-death from a message a client publishes: its history starts again at 1.
        // Found while building; keep your own count in a header if you need one.
        assertThat(((Number) death.get("count")).longValue()).isEqualTo(1);
    }

    @Test
    void nothingParkedMovesNothing() throws Exception {
        mvc.perform(post("/dead-letters/replay")).andExpect(status().isOk()).andExpect(jsonPath("$.moved").value(0));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 35 minutes

## Urgent reports first

`POST /lab-reports/{id}/render?urgent=true` sends the message with a higher priority on a queue that supports priorities, so it is the next message any worker takes.

**Done when:** the test in `UrgentReportsChallengeTest` passes.

Hints

- The queue needs `x-max-priority`; a queue's arguments cannot change in place, so in production this is a new queue or a migration.
- A message post-processor sets the priority when publishing.
- Priority only reorders what is waiting; prefetch 1 keeps little waiting inside the workers.

#### `challenge/UrgentReportsChallengeTest.java`

``` code
package com.mediqo.reports;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: an emergency ward cannot wait behind the morning's routine reports. POST
 * /lab-reports/{id}/render?urgent=true sends the message with a higher priority, on a queue that supports priorities,
 * so it is the next one any worker takes.
 */
class UrgentReportsChallengeTest extends ApiTest {

    @Test
    void anUrgentReportJumpsTheQueue() throws Exception {
        render("LR-0401").andExpect(status().isAccepted());   // both workers busy for 2 s
        render("LR-0402").andExpect(status().isAccepted());
        for (String routine : new String[]{"LR-0201", "LR-0202", "LR-0203"}) {
            render(routine).andExpect(status().isAccepted());
        }
        mvc.perform(post("/lab-reports/LR-0005/render").param("urgent", "true")).andExpect(status().isAccepted());

        awaitStatus("LR-0005", "READY");
        // When the urgent one is done, none of the routine ones queued before it is.
        long routineDone = java.util.stream.Stream.of("LR-0201", "LR-0202", "LR-0203")
                .filter(id -> {
                    try {
                        return report(id).path("status").asString().equals("READY");
                    } catch (Exception e) {
                        throw new IllegalStateException(e);
                    }
                }).count();
        assertThat(routineDone).isZero();
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## RabbitMQ or Kafka?

Mediqo also wants every lab result as an event that billing, the patient app and analytics read on their own, and can read again from last month. Which part stays a RabbitMQ work queue and which becomes a Kafka topic? Compare: who removes a message, whether consumers compete or each read everything, replay, ordering, and Kafka's newer share groups (queue-like consumption on a topic). Where does each one's dead letter go?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test with the plain client: auto-ack against manual ack.
2.  Declare the topology: exchange, durable queue, dead-letter exchange and queue.
3.  Publish with confirms; consume with acknowledgement after the work, prefetch 1.
4.  Add retry, the recoverer and idempotency; then cut a worker off in a test.

## Design alternatives and trade-offs

| Approach                                             | What it costs                                                                                               | Verdict                     |
|------------------------------------------------------|-------------------------------------------------------------------------------------------------------------|-----------------------------|
| Acknowledge after the work, retry, dead-letter queue | Repeats are possible: the worker must skip them.                                                            | Chosen                      |
| Auto-ack (`acknowledge-mode: none`)                  | A worker that dies loses its messages.                                                                      | The trap                    |
| Requeue on every failure                             | A message that always fails loops for ever.                                                                 | Avoid                       |
| @Async in the app (station 098's way)                | No broker; jobs die with the server.                                                                        | For work you can lose       |
| Kafka                                                | A log that consumers read at their own pace and can replay; work-queue semantics need share groups or care. | For events, see challenge 3 |

## Database design

No database: the broker holds the work, the disk holds the reports. With several servers, report state moves to a table and files to object storage; the queue stays the same.

# 3 · Go deeper: Production

Quorum queues  
On a RabbitMQ cluster, use quorum queues for work that must survive a node: classic queues live on one node.

Watch  
Queue depth, unacknowledged messages, consumer count and the dead-letter queue's size. A growing dead-letter queue is a bug report.

Timeouts  
RabbitMQ closes a channel whose delivery is not acknowledged within `consumer_timeout` (30 minutes by default): long tasks must fit, or be split.

Poison messages  
The retry limit is what keeps one bad message from blocking a worker for ever.

Outbox  
If the request also writes a database row, publish through an outbox table, or a crash between the two loses one of them.

# 3 · Go deeper: Interview

## Interview takeaways

Why do messages get lost with auto-ack?

The broker deletes a message as soon as it is sent to a consumer. If the consumer dies before finishing, nobody has it.

What does Spring AMQP's acknowledge-mode auto mean?

Spring acknowledges after the listener returns normally and rejects on an exception: the safe default. RabbitMQ's autoAck is Spring's NONE.

What is prefetch for?

How many unacknowledged messages a consumer may hold. 1 spreads long tasks fairly; higher is faster for tiny ones.

How do you stop a poison message looping?

Retry a few times, then reject without requeue so the broker dead-letters it.

How does the API know the broker has the message?

Publisher confirms: wait for the broker's ack before answering 202.

Why must consumers be idempotent?

Delivery is at least once: a crash after the work and before the ack means the message comes again.

## Self-check rubric

| Area        | Meets the bar                   | Above the bar                                                                             |
|-------------|---------------------------------|-------------------------------------------------------------------------------------------|
| Correctness | All 12 tests pass.              | You ran the flawed version and explained each failure.                                    |
| Delivery    | Durable queue, acks after work. | Publisher confirms, prefetch chosen on purpose, idempotent worker.                        |
| Failure     | Retries.                        | A retry limit, a dead-letter queue, and the reason recorded.                              |
| Testing     | A listener test.                | A real broker, a worker cut off mid-task, and a test that fails without acknowledgements. |

# 3 · Go deeper: Review

## The pull request

A teammate "speeds up the workers": a listener container factory with `AcknowledgeMode.NONE`, "so the worker is simpler without acknowledgements". Read the file and list every problem before opening the findings.

#### `review/ReportsApplication.java`

``` code
package com.mediqo.reports;

import org.springframework.amqp.core.AcknowledgeMode;
import org.springframework.amqp.core.Binding;
import org.springframework.amqp.core.BindingBuilder;
import org.springframework.amqp.core.Declarables;
import org.springframework.amqp.core.DirectExchange;
import org.springframework.amqp.core.Queue;
import org.springframework.amqp.core.QueueBuilder;
import org.springframework.amqp.rabbit.config.SimpleRabbitListenerContainerFactory;
import org.springframework.amqp.rabbit.connection.ConnectionFactory;
import org.springframework.amqp.support.converter.JacksonJsonMessageConverter;
import org.springframework.amqp.support.converter.MessageConverter;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

@SpringBootApplication
public class ReportsApplication {

    static final String EXCHANGE = "lab-reports";
    static final String QUEUE = "report-render";
    static final String DEAD_LETTERS = "lab-reports.dlx";
    static final String DEAD_LETTER_QUEUE = "report-render.dlq";
    static final String ROUTING_KEY = "render";

    public static void main(String[] args) {
        SpringApplication.run(ReportsApplication.class, args);
    }

    /**
     * Declared on start-up if missing: a direct exchange routes "render" to the durable work queue; a message the
     * worker gives up on goes to the dead-letter exchange and waits in its own queue for a person.
     */
    @Bean
    Declarables topology() {
        DirectExchange exchange = new DirectExchange(EXCHANGE);
        DirectExchange deadLetters = new DirectExchange(DEAD_LETTERS);
        Queue work = QueueBuilder.durable(QUEUE).deadLetterExchange(DEAD_LETTERS).deadLetterRoutingKey(ROUTING_KEY).build();
        Queue parked = QueueBuilder.durable(DEAD_LETTER_QUEUE).build();
        Binding route = BindingBuilder.bind(work).to(exchange).with(ROUTING_KEY);
        Binding parkedRoute = BindingBuilder.bind(parked).to(deadLetters).with(ROUTING_KEY);
        return new Declarables(exchange, deadLetters, work, parked, route, parkedRoute);
    }

    /** Auto-ack: faster, and the worker is simpler without acknowledgements. */
    @Bean
    SimpleRabbitListenerContainerFactory rabbitListenerContainerFactory(ConnectionFactory connections, MessageConverter json) {
        SimpleRabbitListenerContainerFactory factory = new SimpleRabbitListenerContainerFactory();
        factory.setConnectionFactory(connections);
        factory.setMessageConverter(json);
        factory.setAcknowledgeMode(AcknowledgeMode.NONE);
        factory.setConcurrentConsumers(2);
        return factory;
    }

    /** Messages as JSON, readable in the management UI. */
    @Bean
    MessageConverter json() {
        return new JacksonJsonMessageConverter();
    }
}
```

## Findings

1AcknowledgeMode.NONE

"Auto-ack: faster": the broker now deletes each message the moment a worker receives it. A worker that dies mid-report loses it, and a listener that throws loses it too: there is nothing left to retry or dead-letter.

**Test evidence:** `aWorkerCutOffMidRenderLosesNothing` and `aDamagedReportEndsInTheDeadLetterQueueWithItsReason` fail.

2A hand-made factory drops Spring Boot's settings

Declaring `rabbitListenerContainerFactory` replaces the one Spring Boot builds from `application.yaml`: prefetch 1, the retry policy and the recoverer are all gone, with nothing in the code to say so.

**Test evidence:** `aSlowReportDoesNotHoldUpTheOnesBehindIt` and `aBusyLabSystemIsRetriedAndTheReportIsRendered` fail: no prefetch 1, no retry.

## Same tests, flawed version

From `docs/review-run.txt`: the flawed file copied over the real one, then the full suite run.

| Test class                        | Fixed version | Flawed version |
|-----------------------------------|---------------|----------------|
| `AutoAckTrapTest`                 | 2 / 2         | 2 / 2          |
| `BrokerDownTest`                  | 1 / 1         | 1 / 1          |
| `DuplicateRenderReplayTest`       | 2 / 2         | 2 / 2          |
| `RenderContractTest`              | 4 / 4         | 3 / 4          |
| `RetryAndDeadLetterMessagingTest` | 3 / 3         | 0 / 3          |

On a calm day with healthy workers, every report is rendered. The flaw shows on the day a server restarts at peak: exactly the day in the story.
