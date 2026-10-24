# Station 104 · Enterprise integration with Apache Camel

Working Systems · 0–2 years · Core · Insurance · Types: Messaging, Idempotency

Spring Boot 4.1.1 · Java 25 · Apache Camel 4.23 (SFTP, file, idempotent consumer, error handling) · RabbitMQ 4.1 · Spring AMQP · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (RabbitMQ and the bank's SFTP server for the app; Testcontainers starts its own for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** The partner bank and its SFTP server are simulated (an SFTP server in Docker with demo files). Nothing is issued: valid lines become messages on a queue.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 10 tests.

# 1 · Understand

## The problem in real life

1.  **Files at 2 am**

    Partner banks sell Bimaly's insurance. Each night a bank drops a file of new policies on its SFTP server. 4,000 lines of home-made glue code read the files and put each policy on a queue for the issuance team.

2.  **Every policy twice**

    One night the app was restarted for a deployment. The glue code had kept the list of files it had read in memory. After the restart it read the whole folder again, and the issuance team received every policy of the last month a second time.

3.  **The fix**

    A short Camel route replaces the glue code. What has been processed is recorded on disk, by the file's content; a restart, or the bank sending the same file again, changes nothing. Bad lines are rejected with their reason, unreadable files are put aside, and a broker problem is retried.

Whatever must not happen twice needs a record that outlives the process. Memory is gone at the next restart.

## What are we building?

A route that reads a bank's policy files from SFTP, checks them, and puts each valid policy on a queue exactly once per file, with a record of every run.

## An everyday analogy

An accounts clerk who receives invoices by post. Each one is stamped "entered" in a ledger before it is paid. If the supplier posts the same invoice twice, or the clerk goes home and comes back, the ledger says it is done. A torn, unreadable invoice goes into a tray for the manager, not into the bin.

## How it works in 4 steps

1.  **Poll**: every 30 s, look in the bank's folder for files not seen before.
2.  **Check the record**: a file whose content was already processed is noted as a duplicate and skipped.
3.  **Validate**: a file that cannot be read goes to the dead-letter folder; a bad line is rejected with its reason.
4.  **Send**: valid lines go to the queue; the run is done only when the broker has confirmed every one.

Check yourself: why not just delete the file after reading it?

It is the bank's folder, and the bank allows us to read only. Even where moving files is allowed, a crash between "sent" and "moved" leaves the file to be read again: you still need a record.

## What this station is not

- **No real bank.** An SFTP server in Docker with demo files.
- **No policy issuance.** That team reads the queue; here we only fill it.
- **Not one server per bank.** One bank, one folder; more banks are more routes of the same shape.

## Key terms

| Term                    | Simple meaning                                                                                    | Everyday example                                       | In this project         |
|-------------------------|---------------------------------------------------------------------------------------------------|--------------------------------------------------------|-------------------------|
| **Integration route**   | A pipeline that takes something from one system, changes or checks it, and hands it to another.   | A sorting office: letters in, sorted, out to the vans. | SFTP → validate → queue |
| **Apache Camel**        | A library of ready connectors ("components") and patterns for writing such routes in a few lines. | A box of standard pipe fittings.                       | `PolicyFileRoute`       |
| **SFTP polling**        | Looking in a remote folder every so often for new files.                                          | Checking the letterbox every half hour.                | every 30 s              |
| **Idempotent consumer** | Remembers what it already handled and skips it if it comes again.                                 | Ticking off invoices already paid.                     | two records on disk     |
| **Dead-letter channel** | Where a message that can never be processed is put aside for a person.                            | The "return to sender" tray.                           | `data/dead-letter/`     |
| **Redelivery**          | Trying a failed step again after a short wait, in case the problem passes.                        | Ringing back when the line was busy.                   | 3 times, 2 s apart      |

# 2 · Build: Spec

## Business problem

**Bimaly** (a fictional insurance broker) receives nightly policy files from partner banks on SFTP. The glue code that reads them is 4,000 lines long and sent a month of policies twice after a restart.

## Acceptance criteria

Demo rules: files named `BANK-YYYYMMDD.csv`, UTF-8, with the header `reference,customer_name,date_of_birth,product_code,sum_insured_paise`, five columns without commas or quotes inside them, at most 10,000 lines; a poll every 30 s; a failed step tried 3 more times, 2 s apart.

1.  **Given** a good file, **then** every line is one message on `policy.requests` with the id `BANK:REFERENCE`, and the run is `DONE`.
2.  **Given** bad lines, **then** each is rejected with its line number and reason, and the others are sent.
3.  **Given** a file that cannot be read (name, header, encoding, empty), **then** nothing is sent, the file goes to the dead-letter folder as it arrived, and it is not tried again.
4.  **Given** the broker refuses, **then** the step is retried; if it still fails, the run is `FAILED` and the next poll tries the file again.
5.  **Given** a restart, or the same content uploaded again, **then** nothing is sent twice; a re-upload is recorded as `DUPLICATE`.
6.  **Given** `GET /integration/runs/{id}`, **then** `200` with what happened, `404` for an unknown run, `400` for a non-number.

## Requirements

- The bank's folder is read-only to us: files are never moved or deleted there.
- What was processed is recorded on disk, by content.
- Errors that will pass are retried; errors that never will are put aside at once.

## Learning objectives

- Write a Camel route with the SFTP and file components.
- Use an idempotent consumer with a store that survives restarts.
- Separate retryable errors from dead letters with `onException`.
- Publish to RabbitMQ with confirms and stable message ids.
- Test a route against a real SFTP server and broker, including a restart.

# 2 · Build: API contract

## The route and the endpoint

| What                 | Where                                          | Purpose                                                                                 |
|----------------------|------------------------------------------------|-----------------------------------------------------------------------------------------|
| Route `policy-files` | `sftp://koshbank@…/upload` → `policy.requests` | Poll the bank's folder; validate; queue each valid line.                                |
| `GET`                | `/integration/runs/{id}`                       | What happened to one file: status, lines, accepted, rejected lines with reasons, error. |

## Run statuses

| Status        | Meaning                                                                          |
|---------------|----------------------------------------------------------------------------------|
| DONE          | Valid lines sent and confirmed by the broker                                     |
| DUPLICATE     | The same content was already processed; nothing sent                             |
| FAILED        | A step kept failing; the next poll tries the file again                          |
| DEAD_LETTERED | The file can never be processed as it is; a copy waits in the dead-letter folder |
| RUNNING       | Being processed now                                                              |

## Captured examples

Captured on 24 Oct 2026 by `docs/capture.sh`: three files uploaded at once (one poll takes them in name order), then the first again, then one while the broker refuses. `Date`, connection and standard security headers are left out.

### Run 1: a good file

**Why:** three lines, three messages.

Request

``` code
GET /integration/runs/1 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 274

{
  "accepted": 3,
  "checksum": "8d862bc8676f0925b025036bd368de2201aaef8256a0e667329a954d026e24e6",
  "error": null,
  "file": "KOSHBANK-20261022.csv",
  "finishedAt": "2026-10-24T18:19:39.537739682Z",
  "id": 1,
  "lines": 3,
  "rejected": [],
  "startedAt": "2026-10-24T18:19:39.296569892Z",
  "status": "DONE"
}
```

### Run 2: a file with bad lines

**Why:** one line sent; three rejected, each with its line number and reason.

Request

``` code
GET /integration/runs/2 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 515

{
  "accepted": 1,
  "checksum": "00f3a2ced4e53a84fa5e2a8d583b7e87394bf106985f2962ef50c27e750326e0",
  "error": null,
  "file": "KOSHBANK-20261023.csv",
  "finishedAt": "2026-10-24T18:19:39.589464194Z",
  "id": 2,
  "lines": 4,
  "rejected": [
    {
      "line": 3,
      "reference": "KB-1102",
      "reason": "the date of birth must be in the past"
    },
    {
      "line": 4,
      "reference": "KB-1103",
      "reason": "expected 5 columns, found 4"
    },
    {
      "line": 5,
      "reference": "KB-1101",
      "reason": "reference KB-1101 already appears on line 2"
    }
  ],
  "startedAt": "2026-10-24T18:19:39.571093010Z",
  "status": "DONE"
}
```

### Run 3: a file with semicolons

**Why:** the header is wrong: dead-lettered at once, no retry.

Request

``` code
GET /integration/runs/3 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 383

{
  "accepted": 0,
  "checksum": "55ea5553a0c1793d65cb1fac3f0717bdb19837911b98c7036103556f9903c278",
  "error": "The first line is not the header reference,customer_name,date_of_birth,product_code,sum_insured_paise.",
  "file": "KOSHBANK-20261024.csv",
  "finishedAt": "2026-10-24T18:19:39.610494764Z",
  "id": 3,
  "lines": 0,
  "rejected": [],
  "startedAt": "2026-10-24T18:19:39.602476542Z",
  "status": "DEAD_LETTERED"
}
```

``` code
data/dead-letter/KOSHBANK-20261024.csv: the file as it arrived (identical bytes)
```

The queue after runs 1 to 3, read through RabbitMQ's management API without taking the messages off (message id, delivery mode 2 = persistent, body):

``` code
4 messages on policy.requests
KOSHBANK:KB-1001 2 {"bank":"KOSHBANK","reference":"KB-1001","customerName":"Meera Iyer","dateOfBirth":"1988-04-12","productCode":"TERM10","sumInsuredPaise":1000000000}
KOSHBANK:KB-1002 2 {"bank":"KOSHBANK","reference":"KB-1002","customerName":"Ravi Kumar","dateOfBirth":"1975-11-02","productCode":"HEALTH5","sumInsuredPaise":50000000}
KOSHBANK:KB-1003 2 {"bank":"KOSHBANK","reference":"KB-1003","customerName":"Asha Rao","dateOfBirth":"1990-06-30","productCode":"HEALTH5","sumInsuredPaise":50000000}
KOSHBANK:KB-1101 2 {"bank":"KOSHBANK","reference":"KB-1101","customerName":"Vikram Shah","dateOfBirth":"1982-01-15","productCode":"TERM10","sumInsuredPaise":2500000000}
```

### Run 4: the bank uploads run 1's file again

**Why:** same content: a duplicate, nothing sent.

Request

``` code
GET /integration/runs/4 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 316

{
  "accepted": 0,
  "checksum": "8d862bc8676f0925b025036bd368de2201aaef8256a0e667329a954d026e24e6",
  "error": "The same content was already processed.",
  "file": "KOSHBANK-20261022.csv",
  "finishedAt": "2026-10-24T18:20:09.645024402Z",
  "id": 4,
  "lines": 0,
  "rejected": [],
  "startedAt": "2026-10-24T18:20:09.643820024Z",
  "status": "DUPLICATE"
}
```

### Run 5: the broker refuses every message

**Why:** 3 retries 2 s apart, then `FAILED`; the file is not marked as processed.

Request

``` code
GET /integration/runs/5 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 309

{
  "accepted": 1,
  "checksum": "f68df4ea0d7c1d84594be51643242187c80f5bc3bed92cba83855cba92a3660e",
  "error": "java.io.IOException: nacks received",
  "file": "KOSHBANK-20261025.csv",
  "finishedAt": "2026-10-24T18:20:45.696947969Z",
  "id": 5,
  "lines": 1,
  "rejected": [],
  "startedAt": "2026-10-24T18:20:39.661179233Z",
  "status": "FAILED"
}
```

### Run 6: the broker is back

**Why:** the next poll picked the same file up again: `DONE`.

Request

``` code
GET /integration/runs/6 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 274

{
  "accepted": 1,
  "checksum": "f68df4ea0d7c1d84594be51643242187c80f5bc3bed92cba83855cba92a3660e",
  "error": null,
  "file": "KOSHBANK-20261025.csv",
  "finishedAt": "2026-10-24T18:21:15.743546861Z",
  "id": 6,
  "lines": 1,
  "rejected": [],
  "startedAt": "2026-10-24T18:21:15.737763520Z",
  "status": "DONE"
}
```

### No such run

**Why:** `404`.

Request

``` code
GET /integration/runs/99 HTTP/1.1
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "instance": "/integration/runs/99",
  "status": 404,
  "title": "Not Found"
}
```

### Not a run number

**Why:** `400`.

Request

``` code
GET /integration/runs/latest HTTP/1.1
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Failed to convert 'id' with value: 'latest'",
  "instance": "/integration/runs/latest",
  "status": 400,
  "title": "Bad Request"
}
```

## What the app remembers

The two records on disk at the end of the capture:

``` code
data/processed-files.dat (SHA-256 of each processed file's content):
8d862bc8676f0925b025036bd368de2201aaef8256a0e667329a954d026e24e6
00f3a2ced4e53a84fa5e2a8d583b7e87394bf106985f2962ef50c27e750326e0
f68df4ea0d7c1d84594be51643242187c80f5bc3bed92cba83855cba92a3660e

data/seen-files.dat (name-size-time of each downloaded file):
KOSHBANK-20261022.csv-209-1792865978000
KOSHBANK-20261024.csv-73-1792865978000
KOSHBANK-20261023.csv-251-1792865978000
KOSHBANK-20261022.csv-209-1792865981000
KOSHBANK-20261025.csv-117-1792866011000
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                           | What happens                                                         | Proved by                                                         |
|----------------------------------------------------------------|----------------------------------------------------------------------|-------------------------------------------------------------------|
| The old route, restarted                                       | The same file read again                                             | `theOldRouteReadsTheSameFileAgainAfterARestart`                   |
| The app, restarted; then the same file under a new name        | Processed once; then `DUPLICATE`                                     | `theApiRemembersWhatItProcessedAcrossARestart`                    |
| A good file                                                    | `DONE`; one message per line, id `BANK:REFERENCE`, codes upper-cased | `aFileIsCheckedAndItsValidLinesQueued`                            |
| Missing column, future birth date, bad sum, repeated reference | Rejected with line number and reason; the rest sent                  | `badLinesAreRejectedWithTheirReasonAndTheOthersGoOn`              |
| Unknown run; not a number                                      | `404`; `400`                                                         | `anUnknownRunIs404AndANonNumberIs400`                             |
| The broker refuses                                             | Retried, `FAILED`, then `DONE` on a later poll                       | `aBrokerThatRefusesIsRetriedThenTheFileIsTriedAgainOnTheNextPoll` |
| A wrong header                                                 | Dead-lettered once, as it arrived                                    | `aFileThatCanNeverBeReadGoesToTheDeadLetterFolderOnce`            |
| A wrong name; a header only                                    | Dead-lettered                                                        | `aWrongFileNameOrAnEmptyFileIsDeadLetteredToo`                    |
| The same file uploaded again, same or new name                 | `DUPLICATE`; nothing sent                                            | `theSameFileUploadedAgainSendsNothingAndIsRecordedAsADuplicate`   |
| A corrected file with the same name                            | Processed; unchanged lines sent again with the same ids              | `aCorrectedFileWithTheSameNameIsProcessed`                        |

## The trap

Plausible but wrong

Processing the same file twice after a restart because nothing records what was already consumed.

- **The old way.** The bank's folder is read-only, so the route uses `noop=true`, and Camel then remembers the files it read. In memory: within one run the file is read once; after a restart (a new Camel context) it is read again.
- **The API.** The app is started, processes the file, is stopped and started again: the file is not processed again. Then the bank uploads the same file under a new name: it is recorded as a duplicate, and the queue still holds only the first two messages.

While building, each part was undone once: the downloaded-files record in memory turned 1 test red; the processed-files record in memory 1; no duplicate check 2; no dead-letter handling 2; every error handled (never retried) 1; no publisher confirms 1; no message ids 5; product codes not upper-cased 1; repeated references allowed 1; birth dates in the future allowed 1.

``` code
package com.bimaly.integration;

import org.apache.camel.builder.RouteBuilder;
import org.apache.camel.impl.DefaultCamelContext;
import org.junit.jupiter.api.Test;
import org.springframework.amqp.rabbit.core.RabbitAdmin;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.util.FileSystemUtils;

import java.nio.file.Path;
import java.time.Duration;
import java.util.concurrent.atomic.AtomicInteger;

import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;

/** The app is restarted at night for a deployment. Written first. */
class FileRestartTrapTest {

    static final String FILE = PolicyFile.HEADER + "\nKB-8001,Meera Iyer,1988-04-12,TERM10,1000000000\nKB-8002,Ravi Kumar,1975-11-02,HEALTH5,50000000\n";

    /** The old way: the bank's folder is read-only, so noop=true, and Camel remembers the files it read in memory. */
    @Test
    void theOldRouteReadsTheSameFileAgainAfterARestart() throws Exception {
        Partners.upload("old", "KOSHBANK-20260101.csv", FILE);
        AtomicInteger processed = new AtomicInteger();
        for (int restart = 1; restart <= 2; restart++) {
            try (var camel = new DefaultCamelContext()) {
                camel.addRoutes(new RouteBuilder() {
                    @Override
                    public void configure() {
                        from(Partners.sftp("old", 200) + "&noop=true").process(e -> processed.incrementAndGet());
                    }
                });
                camel.start();
                int expected = restart;
                await().atMost(Duration.ofSeconds(15)).until(() -> processed.get() == expected);
                Thread.sleep(1_000);   // five more polls: within one run, the file is not read again
                assertThat(processed).hasValue(restart);
            }
        }
        assertThat(processed).as("the same file, processed once per start").hasValue(2);
    }

    /** The API: what was processed is recorded on disk, so a restart starts where the last run stopped. */
    @Test
    void theApiRemembersWhatItProcessedAcrossARestart() throws Exception {
        FileSystemUtils.deleteRecursively(Path.of("target/restart-data").toFile());
        Partners.upload("restart", "KOSHBANK-20260102.csv", FILE);

        try (var first = start()) {
            first.getBean(RabbitAdmin.class).purgeQueue(PolicyQueue.QUEUE);
            Runs runs = first.getBean(Runs.class);
            await().atMost(Duration.ofSeconds(20)).until(() -> runs.forFile("KOSHBANK-20260102.csv"),
                    r -> r.size() == 1 && r.getFirst().status == Runs.Status.DONE);
            assertThat(waiting(first)).isEqualTo(2);
        }
        try (var second = start()) {
            Thread.sleep(2_000);   // ten polls of the same folder
            assertThat(second.getBean(Runs.class).forFile("KOSHBANK-20260102.csv")).hasSize(1);
            assertThat(waiting(second)).as("still the two messages of the first start").isEqualTo(2);

            Partners.upload("restart", "KOSHBANK-20260103.csv", FILE);   // the same file again, under a new name
            await().atMost(Duration.ofSeconds(20)).until(() -> second.getBean(Runs.class).forFile("KOSHBANK-20260103.csv"),
                    r -> r.size() == 1 && r.getFirst().status == Runs.Status.DUPLICATE);
            assertThat(waiting(second)).isEqualTo(2);
        }
    }

    private static ConfigurableApplicationContext start() {
        return new SpringApplicationBuilder(IntegrationApplication.class).run("--server.port=0",
                "--bimaly.files.data=target/restart-data", "--bimaly.partner.uri=" + Partners.sftp("restart", 200),
                "--spring.rabbitmq.host=" + Partners.RABBIT.getHost(), "--spring.rabbitmq.port=" + Partners.RABBIT.getAmqpPort());
    }

    private static long waiting(ConfigurableApplicationContext app) {
        return app.getBean(RabbitAdmin.class).getQueueInfo(PolicyQueue.QUEUE).getMessageCount();
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
docker compose up -d --wait  # RabbitMQ (5672, UI on 15672) and the bank's SFTP server (2222)
./mvnw spring-boot:run       # the route and http://localhost:8080
./mvnw test                  # all 10 tests; starts its own RabbitMQ and SFTP server
```

**Windows (PowerShell)**

``` code
docker compose up -d --wait
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Drop a file in the bank's folder as the bank would, wait for the next poll, and read run 1:

``` code
printf 'reference,customer_name,date_of_birth,product_code,sum_insured_paise\nKB-1,Meera Iyer,1988-04-12,TERM10,1000000000\n' \
  | docker compose exec -T sftp sh -c 'cat > /home/koshbank/upload/KOSHBANK-20261024.part && mv /home/koshbank/upload/KOSHBANK-20261024.part /home/koshbank/upload/KOSHBANK-20261024.csv'
curl localhost:8080/integration/runs/1
```

Stop the app, start it again, and wait for a poll: no run 2. Then delete `data/` while it is stopped and start once more: the file is processed again. That is what the record is for.

## Troubleshooting

| You see                                   | Cause                                                                                     | Fix                                                                                     |
|-------------------------------------------|-------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------|
| `Auth fail` in the log                    | Wrong SFTP user or password.                                                              | Compose's user is `koshbank` / `demo-only`.                                             |
| `reject HostKey`                          | The server's key is not in known_hosts.                                                   | Demo: `strictHostKeyChecking=no`. Production: add the bank's key to a known_hosts file. |
| A file is never picked up                 | Its name does not end in `.csv`, or it was seen before with the same name, size and time. | Check `data/seen-files.dat`.                                                            |
| A run stays FAILED and repeats every poll | The broker keeps refusing.                                                                | Check RabbitMQ's alarms (disk, memory) and queue policies.                              |

## Project layout

``` tree
stations/104-enterprise-integration-with-apache-camel/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/bimaly/integration/
│   ├── PolicyFileRoute.java   ├── PolicyFile.java   ├── PolicyQueue.java   ├── PolicyRequest.java
│   ├── Runs.java   ├── RunController.java   └── IntegrationApplication.java
├── src/main/resources/application.yaml
├── src/test/java/com/bimaly/integration/   (see Tests)
├── data/                     made by the app: runs/, the two records, dead-letter/
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

The route first, then in the order a file travels.

#### `src/main/java/com/bimaly/integration/PolicyFileRoute.java`

Does  
The route.

Why  
Polls the bank's folder, checks the record, validates, sends, and records the run. Two `onException` blocks: never-retry (dead letter) and retry-then-fail.

Without it  
4,000 lines of glue code; a file read twice; a broken file retried for ever.

- `noop=true` because the folder is read-only; `sortBy=file:name` so a poll with several days' files takes them in date order.
- `handled(false)` on the retryable errors is what puts the file back: the record of the file is removed and the next poll sees it again.
- Found in the capture: a dead-lettered file's content is not in `processed-files.dat`. The idempotent consumer removes the key when the exception passes through it, even though `onException` handles it later. The download record is what keeps the file from coming back; a re-upload of the same broken file is dead-lettered again, which is what a person fixing it wants.

#### `src/main/java/com/bimaly/integration/IntegrationApplication.java`

Does  
The two records and the queue.

Why  
`FileIdempotentRepository` twice: downloaded files (name, size, time) and processed content (SHA-256).

Without it  
A restart that forgets.

- Shortcut: files on one server's disk. Two servers polling the same folder need a shared store, such as Camel's JDBC repository.

#### `src/main/java/com/bimaly/integration/PolicyFile.java`

Does  
Reading a file.

Why  
File-level problems throw `BadFileException`; line-level problems become rejected lines with reasons.

Without it  
One bad line losing a whole night's file, or a broken file half-sent.

#### `src/main/java/com/bimaly/integration/PolicyQueue.java`

Does  
Sending.

Why  
All of a file's lines, persistent, with `BANK:REFERENCE` as message id, then waits for the broker's confirms.

Without it  
A run marked done while the broker dropped the messages.

- If the broker fails part-way, the lines already sent are sent again on the retry, with the same ids: the reader drops the copies. Exactly once is not on offer; at least once with stable ids is.

#### `src/main/java/com/bimaly/integration/Runs.java`

Does  
The runs.

Why  
One JSON file per run in `data/runs/`, written to a temporary file and renamed.

Without it  
"What happened to our file?" with no answer.

#### `src/main/java/com/bimaly/integration/RunController.java`

`GET /integration/runs/{id}`.

#### `src/main/java/com/bimaly/integration/PolicyRequest.java`

One valid line, as the issuance team receives it.

#### `src/main/resources/application.yaml`

Does  
Settings.

Why  
The bank's SFTP address, poll interval, retries, the data folder, publisher confirms.

Without it  

- Demo rules: a password and `strictHostKeyChecking=no`. Production uses a private key and pins the bank's host key with `knownHostsFile`.

#### `compose.yaml`

RabbitMQ 4.1 and the simulated bank's SFTP server, each with a health check.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                               | Test class                                                              | Result |
|---------------|-------------------------------------------|-------------------------------------------------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found  | `IntegrationRunContractTest` (3)                                        | pass   |
| Every station | Reproduce the failure before the fix      | `FileRestartTrapTest` (2)                                               | pass   |
| Messaging     | Duplicate delivery, retry and dead letter | `RetryAndDeadLetterMessagingTest` (3), `DuplicateFileReplayTest`        | pass   |
| Idempotency   | The same request twice gives one effect   | `DuplicateFileReplayTest` (2), and the restart in `FileRestartTrapTest` | pass   |

Real servers: RabbitMQ 4.1 and an SFTP server (atmoz/sftp) in Docker. A restart is a real one: the app is started, stopped and started again. The broker's refusal is real too: a queue policy makes it reject every message. Polls every 200 ms and retries 100 ms apart keep the suite fast.

## Run output

JDK 25.0.1, Spring Boot 4.1.1, Camel 4.23.0. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.bimaly.integration.DuplicateFileReplayTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.bimaly.integration.RetryAndDeadLetterMessagingTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.bimaly.integration.IntegrationRunContractTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.bimaly.integration.FileRestartTrapTest
[INFO] Tests run: 10, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/bimaly/integration/FileRestartTrapTest.java`

Written first: the old route and the app, each restarted.

#### `src/test/java/com/bimaly/integration/IntegrationRunContractTest.java`

Good and bad lines; the endpoint.

#### `src/test/java/com/bimaly/integration/RetryAndDeadLetterMessagingTest.java`

A refusing broker; files that can never be read.

#### `src/test/java/com/bimaly/integration/DuplicateFileReplayTest.java`

The same file again; a corrected file.

#### `src/test/java/com/bimaly/integration/ApiTest.java`

Shared setup: fast polls, an empty queue, helpers.

#### `src/test/java/com/bimaly/integration/Partners.java`

RabbitMQ and the bank's SFTP server in Docker; uploads the way banks do them.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/bimaly/integration/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=RunsOfAFileChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 10 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 14 tests pass (10 station tests and 4 challenge tests).

Challenge 1 · Beginner-friendly · about 20 minutes

## What happened to our file?

The bank's support line knows only the file's name. Add `GET /integration/runs?file=NAME`: every run of that file, oldest first; an empty list for a file never seen; `400` without `file`.

**Done when:** both tests in `RunsOfAFileChallengeTest` pass.

Hints

- `Runs.forFile` already exists.
- A required `@RequestParam` gives the `400` for free.

#### `challenge/RunsOfAFileChallengeTest.java`

``` code
package com.bimaly.integration;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: the bank's support line asks "what happened to our file?" and knows only its name. */
class RunsOfAFileChallengeTest extends ApiTest {

    @Test
    void everyRunOfAFileIsListedOldestFirst() throws Exception {
        String file = HEADER + "KB-9101,Meera Iyer,1988-04-12,TERM10,1000000000\n";
        upload("KOSHBANK-20270101.csv", file);
        awaitRun("KOSHBANK-20270101.csv", Runs.Status.DONE);
        Thread.sleep(1_100);
        upload("KOSHBANK-20270101.csv", file);
        awaitRun("KOSHBANK-20270101.csv", Runs.Status.DUPLICATE);

        mvc.perform(get("/integration/runs").param("file", "KOSHBANK-20270101.csv")).andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(2))
                .andExpect(jsonPath("$[0].status").value("DONE")).andExpect(jsonPath("$[1].status").value("DUPLICATE"));
    }

    @Test
    void anUnknownFileHasNoRunsAndTheNameIsRequired() throws Exception {
        mvc.perform(get("/integration/runs").param("file", "KOSHBANK-19990101.csv")).andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(0));
        mvc.perform(get("/integration/runs")).andExpect(status().isBadRequest());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 35 minutes

## Hold a suspicious file

If more than 20% of the lines of a file of 10 lines or more are rejected, the bank's export is probably broken: send nothing, set the run to `HELD` with the reason "3 of 10 lines were rejected; the limit is 20%.", and copy the file as it arrived to `data/held/` for a person. Exactly 20% still goes through; smaller files are judged line by line.

**Done when:** both tests in `HeldFileChallengeTest` pass.

Hints

- A Camel `filter` after validation, ending in `stop()`.
- The body is the parsed file by then: keep the original bytes in an exchange property.
- Compare with whole numbers (`rejected × 100 > lines × 20`), not doubles.

#### `challenge/HeldFileChallengeTest.java`

``` code
package com.bimaly.integration;

import org.junit.jupiter.api.Test;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Challenge 2: when a large share of a file is wrong, the bank's export is probably broken: hold the whole file for a
 * person instead of sending the part that happens to look right. Files under 10 lines are judged line by line.
 */
class HeldFileChallengeTest extends ApiTest {

    static final String GOOD = "KB-92%02d,Meera Iyer,1988-04-12,TERM10,1000000000\n";
    static final String BAD = "KB-92%02d,Meera Iyer,1988-04-12,TERM10\n";

    @Test
    void aFileWithMoreThanOneFifthOfItsLinesWrongIsHeldAndSendsNothing() throws Exception {
        String content = HEADER + lines(1, 7, GOOD) + lines(8, 10, BAD);
        upload("KOSHBANK-20270201.csv", content);
        Runs.Run run = awaitRun("KOSHBANK-20270201.csv", Runs.Status.HELD);

        assertThat(run.error).isEqualTo("3 of 10 lines were rejected; the limit is 20%.");
        assertThat(run.rejected).hasSize(3);
        assertThat(Files.readString(Path.of("target/test-data/held/KOSHBANK-20270201.csv"))).isEqualTo(content);
        assertThat(waiting()).isZero();
    }

    @Test
    void oneFifthIsStillAllowedAndASmallFileIsJudgedLineByLine() throws Exception {
        upload("KOSHBANK-20270202.csv", HEADER + lines(11, 18, GOOD) + lines(19, 20, BAD));
        assertThat(awaitRun("KOSHBANK-20270202.csv", Runs.Status.DONE).accepted).isEqualTo(8);
        upload("KOSHBANK-20270203.csv", HEADER + lines(21, 22, GOOD) + lines(23, 25, BAD));
        assertThat(awaitRun("KOSHBANK-20270203.csv", Runs.Status.DONE).accepted).isEqualTo(2);
        assertThat(waiting()).isEqualTo(10);
    }

    private static String lines(int from, int to, String format) {
        StringBuilder s = new StringBuilder();
        for (int i = from; i <= to; i++) {
            s.append(format.formatted(i));
        }
        return s.toString();
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Two servers, one folder

For availability, the app now runs on two servers, and both poll the same bank folder. Each keeps its records on its own disk. Write down what happens when a file arrives, then design the fix: a shared store for the records (which, and what does "add if absent" need from it?), or only one server polling at a time (how is the other told to take over?). What does the issuance team see in each failure case?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: the route with `noop=true`, restarted.
2.  Record processed content on disk with an idempotent consumer; record downloaded files too.
3.  Validate: file-level errors as one exception type, line-level errors as rejected lines.
4.  Two `onException` blocks: dead letter for the first, retry-then-fail for everything else.
5.  Send with confirms and stable ids; record each run.

## Design alternatives and trade-offs

| Approach                                | What it costs                                                    | Verdict                      |
|-----------------------------------------|------------------------------------------------------------------|------------------------------|
| Idempotent consumer, records on disk    | Two small files; one server only.                                | Chosen                       |
| `noop=true` alone                       | Remembers in memory: forgotten at the next restart.              | The trap                     |
| Move or delete files after reading      | Needs write access; a crash between send and move still repeats. | Where allowed, with a record |
| Records in a database (JDBC repository) | A database to run; works for several servers.                    | Next step at scale           |
| One dead-letter channel for every error | A broker blip parks good files for a person.                     | Separate them                |
| Keep the hand-written glue code         | 4,000 lines to maintain; each pattern written again.             | Replace                      |

## Database design

No database in this station. What a table would hold is kept in files under `data/`:

| File                  | Holds                                              | Why                                             |
|-----------------------|----------------------------------------------------|-------------------------------------------------|
| `processed-files.dat` | SHA-256 of each processed file's content           | The record that stops a second processing.      |
| `seen-files.dat`      | name-size-time of each downloaded file             | Saves downloading every file after a restart.   |
| `runs/N.json`         | One run per file picked up                         | What happened, for people.                      |
| `dead-letter/`        | Files that can never be processed, as they arrived | For a person to fix and ask the bank to resend. |

**Boundaries:** the content's key is added before the lines are sent and removed if sending fails, so a failed file is tried again. A file is `DONE` only after the broker confirmed every message.

# 3 · Go deeper: Production

## Real-world considerations

Watching it  
A file expected every night and not seen by 3 am is the alert that matters most: a missing file is silent. Count runs by status; any `DEAD_LETTERED` or repeated `FAILED` wants a person.

Half-written files  
Banks upload as `.part` and rename. If a bank cannot, use Camel's read locks (`readLock=changed`) so a file still growing is not read.

Keys and secrets  
An SSH key per bank, held in a secret store; the bank's host key pinned. Never `strictHostKeyChecking=no` outside a demo.

Growth of the records  
`FileIdempotentRepository` keeps up to 32 MB by default and then drops the oldest entries. A file older than that, uploaded again, would be processed again: size it, or move the records to a database.

More banks  
One route per bank from the same builder, each with its own folder, user and records.

Exactly once  
Not on offer between a file and a queue. At least once, with `BANK:REFERENCE` as message id, lets the reader drop copies.

# 3 · Go deeper: Interview

## Interview takeaways

What is Apache Camel for?

Integration routes: ready components (SFTP, file, AMQP, HTTP and hundreds more) and enterprise integration patterns, so the glue is a few lines instead of thousands.

What does noop=true do on a file or SFTP consumer?

Leaves files where they are and turns on an idempotent repository so each is read once: by default in memory, so a restart reads them again.

What is an idempotent consumer?

It records a key for each message handled and skips messages whose key it has seen. The key and the store decide what "the same" and "remembered" mean.

Which errors go to a dead-letter channel?

The ones that will never succeed as they are: a broken file. Ones that may pass, like a broker outage, get retries and then come back later.

How do you know the broker has the messages?

Publisher confirms: wait until the broker acknowledges each message before marking the work done.

How do you test a restart?

Really restart: start the app, process, stop it, start a new one on the same data, and check nothing happens twice.

## Self-check rubric

| Area        | Meets the bar                     | Above the bar                                                                            |
|-------------|-----------------------------------|------------------------------------------------------------------------------------------|
| Correctness | All 10 tests pass.                | You ran the flawed version and explained each failure.                                   |
| Idempotency | A persistent record.              | You can say what counts as "the same file" and what the record's limits are.             |
| Errors      | Retries and a dead-letter folder. | Retryable and never-retry errors separated, each with a run status a person understands. |
| Camel       | A working route.                  | You can read the route aloud as the business process it is.                              |

# 3 · Go deeper: Review

## The pull request

A teammate "simplifies" the route: "noop already makes it idempotent, and one dead-letter channel means nothing is ever lost". Read the file and list every problem before opening the findings.

#### `review/PolicyFileRoute.java`

``` code
package com.bimaly.integration;

import org.apache.camel.Exchange;
import org.apache.camel.builder.RouteBuilder;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Duration;
import java.util.HexFormat;

/** The bank's SFTP folder → validate each file → valid lines on the policy-requests queue. One run per file. */
@Component
class PolicyFileRoute extends RouteBuilder {

    private static final String RUN = "bimalyRun";
    private final Runs runs;
    private final PolicyQueue queue;
    private final String partner;
    private final String deadLetter;
    private final int redeliveries;
    private final Duration redeliveryDelay;

    PolicyFileRoute(Runs runs, PolicyQueue queue,
                    @Value("${bimaly.partner.uri}") String partner, @Value("${bimaly.files.data}") String data,
                    @Value("${bimaly.files.redeliveries}") int redeliveries,
                    @Value("${bimaly.files.redelivery-delay}") Duration redeliveryDelay) {
        this.runs = runs;
        this.queue = queue;
        this.partner = partner;
        this.deadLetter = "file:" + data + "/dead-letter";
        this.redeliveries = redeliveries;
        this.redeliveryDelay = redeliveryDelay;
    }

    @Override
    public void configure() {
        // One error handler for everything: try again, then park the file in the dead-letter folder. Nothing is lost.
        errorHandler(deadLetterChannel("direct:dead-letter").useOriginalMessage()
                .maximumRedeliveries(redeliveries).redeliveryDelay(redeliveryDelay.toMillis()));
        from("direct:dead-letter")
                .process(e -> runs.finish(run(e), Runs.Status.DEAD_LETTERED, e.getProperty(Exchange.EXCEPTION_CAUGHT, Exception.class).getMessage()))
                .to(deadLetter);

        // noop=true: Camel's file components are idempotent with noop, so each file is only ever read once.
        from(partner + "&noop=true&include=.*\\.csv&sortBy=file:name")
                .routeId("policy-files")
                .process(this::start)
                .process(this::validate)
                .process(e -> queue.sendAll(e.getMessage().getBody(PolicyFile.Parsed.class).accepted()))
                .process(e -> runs.finish(run(e), Runs.Status.DONE, null));
    }

    private void start(Exchange e) throws NoSuchAlgorithmException {
        byte[] content = e.getMessage().getBody(byte[].class);
        String checksum = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(content));
        e.setProperty(RUN, runs.start(e.getMessage().getHeader(Exchange.FILE_NAME_ONLY, String.class), checksum));
    }

    private void validate(Exchange e) {
        PolicyFile.Parsed parsed = PolicyFile.parse(run(e).file, e.getMessage().getBody(byte[].class));
        Runs.Run run = run(e);
        run.lines = parsed.lines();
        run.accepted = parsed.accepted().size();
        run.rejected = parsed.rejected();
        e.getMessage().setBody(parsed);
    }

    private static Runs.Run run(Exchange e) {
        return e.getProperty(RUN, Runs.Run.class);
    }
}
```

## Findings

1noop=true remembers in memory

"Camel's file components are idempotent with noop, so each file is only ever read once": once per start. Its default record lives in memory. The next deployment reads the whole folder again, and every policy in it is sent a second time. A re-upload by the bank is not caught either.

**Test evidence:** `theApiRemembersWhatItProcessedAcrossARestart`, `theSameFileUploadedAgainSendsNothingAndIsRecordedAsADuplicate` and `aCorrectedFileWithTheSameNameIsProcessed` fail.

2A broker blip parks good files

"One error handler for everything: nothing is lost": nothing is lost, but a file that failed only because the broker was busy for a minute is moved to the dead-letter folder and waits for a person, and its policies wait with it. Errors that pass should come back on their own.

**Test evidence:** `aBrokerThatRefusesIsRetriedThenTheFileIsTriedAgainOnTheNextPoll` fails: the run is `DEAD_LETTERED`, never `DONE`.

## Same tests, flawed version

From `docs/review-run.txt`: the flawed file copied over the real one, then the full suite run.

| Test class                        | Fixed version | Flawed version |
|-----------------------------------|---------------|----------------|
| `IntegrationRunContractTest`      | 3 / 3         | 3 / 3          |
| `DuplicateFileReplayTest`         | 2 / 2         | 0 / 2          |
| `FileRestartTrapTest`             | 2 / 2         | 1 / 2          |
| `RetryAndDeadLetterMessagingTest` | 3 / 3         | 2 / 3          |

Until the first restart, the flawed version behaves. The first deployment after go-live is when the issuance team sees every policy twice.
