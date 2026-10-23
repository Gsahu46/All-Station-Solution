# Station 092 · KYC document upload

Working Systems · 0–2 years · Core · Fintech · Types: Security

Spring Boot 4.1.1 · Java 25 · multipart uploads streamed to disk · size limits · type from magic bytes · path traversal · Spring Security 7 (HTTP Basic). Needs JDK 25 (or 21, see Set up & code). No Docker, no database. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** The customers, the reviewer and the documents are demo data. Files are stored in a local folder standing for object storage; the list of documents is kept in memory. No KYC check is done on the documents.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 12 tests.

# 1 · Understand

## The problem in real life

1.  **A 2 GB PAN card**

    Someone uploaded a 2 GB file as a PAN card. The old code read every upload into memory with getBytes(): the server ran out of memory and stopped for everyone.

2.  **A file called ../../etc/passwd**

    Another upload was named ../../etc/passwd. The old code saved it under the name the client sent, so it was written outside the upload folder. A program sent with Content-Type: application/pdf was stored as a "PDF".

3.  **The fix**

    The server refuses anything above 5 MB before reading it, copies files in small pieces, names each file itself, and decides the type from the file's first bytes.

Everything about an upload comes from the client: its size, its name and its type. Limit the first, ignore the second, check the third yourself.

## What are we building?

Customers upload KYC documents (PDF, PNG or JPEG, up to 5 MB) and list their own; a reviewer can list anyone's.

## An everyday analogy

A bank's document counter weighs each envelope first, gives it its own reference number instead of trusting what is written on it, and opens it to check it really is a passport copy.

## How it works in 4 steps

1.  **Refuse big uploads** before reading them: the server's multipart limit answers `413`.
2.  **Read the first bytes**: PDF, PNG or JPEG, or `415`.
3.  **Stream** the file to a name the server chooses, counting and hashing on the way.
4.  **Record** the document with its real type, size, SHA-256 and a cleaned-up display name.

Check yourself: a file named photo.png arrives with Content-Type: image/png, but starts with MZ. What is it?

A Windows program. Name and header are the sender's claim; the first bytes are the file. The upload is refused with `415`: `theApiDecidesTheTypeFromTheBytes`.

## What this station is not

- **No virus scanning.** Checking the type is not checking for malware; real systems scan uploads too.
- **No object storage.** A local folder stands for S3 or similar.
- **No document review.** Nobody checks whether the PAN card is real.

## Key terms

| Term                 | Simple meaning                                                     | Everyday example                                           | In this project       |
|----------------------|--------------------------------------------------------------------|------------------------------------------------------------|-----------------------|
| **Multipart upload** | The way browsers and apps send files in an HTTP request, in parts. | A parcel with a form and a box inside.                     | `multipart/form-data` |
| **Size limit**       | The largest upload accepted, enforced before the file is read.     | A post office scale with a maximum.                        | 5 MB (demo rule)      |
| **Magic bytes**      | The first bytes of a file, which say what it really is.            | Reading the label inside the box, not the sticker outside. | `%PDF-`, PNG, JPEG    |
| **Path traversal**   | A file name with `../` that climbs out of the upload folder.       | A parcel addressed "two doors down".                       | `../../etc/passwd`    |
| **Streaming**        | Copying a file piece by piece, never holding it whole in memory.   | Passing buckets along a line.                              | 8 KB at a time        |
| **KYC**              | Know Your Customer: proving who a customer is with documents.      | Showing ID at a bank.                                      | PAN, passport, ...    |

# 2 · Build: Spec

## Business problem

**Tijori** (a fictional wallet app): a 2 GB "PAN card" upload took the server down; a file named `../../etc/passwd` was accepted.

## Acceptance criteria

Demo users: customers asha (1) and rohan (2), reviewer kavya; password `name-demo-pass`. Demo rules: at most 5 MB; PDF, PNG or JPEG; types PAN, PASSPORT, DRIVING_LICENCE, VOTER_ID.

1.  **Given** a PDF, PNG or JPEG up to 5 MB, **then** `201` with its detected type, size and SHA-256.
2.  **Given** more than 5 MB, **then** `413` before the file is read; nothing stored.
3.  **Given** any other content, whatever its name or header, **then** `415`.
4.  **Given** a file name with `../` or odd characters, **then** the file stays in its folder under a server-made name; the name is only a label.
5.  **Given** another customer's documents, **then** `403`; no sign-in, `401`; an unknown customer (reviewer), `404`.

## Requirements

- No upload is held whole in memory.
- No part of a storage path comes from the client.
- The type is decided from the content.

## Learning objectives

- Set multipart limits and see where they are enforced (the server, not MockMvc).
- Stream uploads with limits of your own as a second line.
- Detect file types by magic bytes.
- Defend against path traversal by never using client names in paths.

# 2 · Build: API contract

## Endpoints

| Method | Path                          | Purpose                                                              |
|--------|-------------------------------|----------------------------------------------------------------------|
| `POST` | `/kyc/{customerId}/documents` | Multipart: `type` and `file`. A customer uploads their own document. |
| `GET`  | `/kyc/{customerId}/documents` | The customer's documents; a reviewer may list any customer's.        |

## Status codes

| Status    | When                                                                         |
|-----------|------------------------------------------------------------------------------|
| 200 / 201 | Listed / stored                                                              |
| 400       | An empty file, an unknown type, no file part                                 |
| 401       | No sign-in, or a wrong password                                              |
| 403       | Another customer's documents; a reviewer uploading                           |
| 404       | A reviewer asking for a customer that does not exist                         |
| 413       | Over 5 MB, refused before the file is read                                   |
| 415       | Not a PDF, PNG or JPEG by its first bytes, whatever its name or Content-Type |

## Captured examples

Captured with curl from the running app on 23 Oct 2026, in this order. JSON bodies are indented for reading; `Date`, connection and standard security headers, and curl's `100 Continue`, are left out.

### Case 1: Asha uploads her PAN card

**Why:** a PDF by its first bytes; stored under a UUID; its SHA-256 recorded.

Request

``` code
GET /kyc/1/documents HTTP/1.1
Authorization: Basic YXNoYTphc2hhLWRlbW8tcGFzcw==
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json
Content-Length: 268

{
  "id": "4cc81ffe-c9d3-415a-9904-7030ecd1a9b4",
  "customerId": 1,
  "type": "PAN",
  "fileName": "pan-card.pdf",
  "contentType": "application/pdf",
  "sizeBytes": 24,
  "sha256": "23bec7b1a0d15392887f661f79b2050ca252d9a967d28efb9a07c98f33f32821",
  "uploadedAt": "2026-10-23T14:54:16.442375857Z"
}
```

### Case 2: a Windows program named pan.pdf, sent as application/pdf

**Why:** it starts with `MZ`: `415`.

Request

``` code
GET /kyc/1/documents HTTP/1.1
Authorization: Basic YXNoYTphc2hhLWRlbW8tcGFzcw==
```

Response

``` code
HTTP/1.1 415 
Content-Type: application/problem+json

{
  "detail": "Only PDF, PNG and JPEG documents are accepted",
  "instance": "/kyc/1/documents",
  "status": 415,
  "title": "Unsupported Media Type"
}
```

### Case 3: the same PDF, named ../../etc/passwd

**Why:** stored in Asha's folder under a UUID; `passwd` is only its label.

Request

``` code
GET /kyc/1/documents HTTP/1.1
Authorization: Basic YXNoYTphc2hhLWRlbW8tcGFzcw==
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json
Content-Length: 262

{
  "id": "ed351016-676b-402b-a7ce-20d11dda7ce2",
  "customerId": 1,
  "type": "PAN",
  "fileName": "passwd",
  "contentType": "application/pdf",
  "sizeBytes": 24,
  "sha256": "23bec7b1a0d15392887f661f79b2050ca252d9a967d28efb9a07c98f33f32821",
  "uploadedAt": "2026-10-23T14:54:16.764005853Z"
}
```

### Case 4: 6 MB

**Why:** the server's multipart limit: `413` before our code runs.

Request

``` code
GET /kyc/1/documents HTTP/1.1
Authorization: Basic YXNoYTphc2hhLWRlbW8tcGFzcw==
```

Response

``` code
HTTP/1.1 413 
Content-Type: application/problem+json

{
  "detail": "Maximum upload size exceeded",
  "instance": "/kyc/1/documents",
  "status": 413,
  "title": "Content Too Large"
}
```

### Case 5: an empty file

**Why:** `400`.

Request

``` code
GET /kyc/1/documents HTTP/1.1
Authorization: Basic YXNoYTphc2hhLWRlbW8tcGFzcw==
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "The file is empty",
  "instance": "/kyc/1/documents",
  "status": 400,
  "title": "Bad Request"
}
```

### Case 6: Asha lists her documents

**Why:** the two she stored.

Request

``` code
GET /kyc/1/documents HTTP/1.1
Authorization: Basic YXNoYTphc2hhLWRlbW8tcGFzcw==
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 533

[
  {
    "id": "4cc81ffe-c9d3-415a-9904-7030ecd1a9b4",
    "customerId": 1,
    "type": "PAN",
    "fileName": "pan-card.pdf",
    "contentType": "application/pdf",
    "sizeBytes": 24,
    "sha256": "23bec7b1a0d15392887f661f79b2050ca252d9a967d28efb9a07c98f33f32821",
    "uploadedAt": "2026-10-23T14:54:16.442375857Z"
  },
  {
    "id": "ed351016-676b-402b-a7ce-20d11dda7ce2",
    "customerId": 1,
    "type": "PAN",
    "fileName": "passwd",
    "contentType": "application/pdf",
    "sizeBytes": 24,
    "sha256": "23bec7b1a0d15392887f661f79b2050ca252d9a967d28efb9a07c98f33f32821",
    "uploadedAt": "2026-10-23T14:54:16.764005853Z"
  }
]
```

### Case 7: Rohan asks for Asha's

**Why:** `403`.

Request

``` code
GET /kyc/1/documents HTTP/1.1
Authorization: Basic cm9oYW46cm9oYW4tZGVtby1wYXNz
```

Response

``` code
HTTP/1.1 403 
Content-Type: application/problem+json
Content-Length: 106

{
  "title": "Not allowed",
  "status": 403,
  "detail": "This sign-in cannot do this.",
  "instance": "/kyc/1/documents"
}
```

### Case 8: no sign-in

**Why:** `401`.

Request

``` code
GET /kyc/1/documents HTTP/1.1
```

Response

``` code
HTTP/1.1 401 
WWW-Authenticate: Basic realm="tijori"
Content-Type: application/problem+json
Content-Length: 118

{
  "title": "Sign-in required",
  "status": 401,
  "detail": "Send a valid username and password.",
  "instance": "/kyc/1/documents"
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                           | What happens                                                               | Proved by                                            |
|----------------------------------------------------------------|----------------------------------------------------------------------------|------------------------------------------------------|
| A PDF                                                          | Stored, its bytes exactly, with size and SHA-256                           | `aDocumentIsStoredWithItsDetectedTypeSizeAndHash`    |
| A PNG sent as application/pdf; a JPEG with no extension        | Typed by its bytes                                                         | `theTypeComesFromTheBytesNotTheHeader`               |
| Empty file, unknown type, no file part; unknown customer       | `400`; `404`                                                               | `badUploadsAre400AndUnknownCustomersAre404`          |
| A name with ../                                                | Kept inside the folder under a UUID                                        | `theApiKeepsEveryFileInsideItsFolderUnderItsOwnName` |
| A program sent as a PDF                                        | `415`, nothing stored                                                      | `theApiDecidesTheTypeFromTheBytes`                   |
| 5 MB; 5 MB + 1 byte; 60 MB                                     | `201`; `413` from the server; `413` or a closed connection, nothing stored | `upToFiveMegabytesIsAcceptedAndMoreIs413`            |
| A 64 MB stream past our own limit                              | Stops after 5 MB and one piece                                             | `theCopyStopsAtTheLimitWithoutReadingTheRest`        |
| No sign-in, wrong password                                     | `401`                                                                      | `withoutAValidSignInIt401s`                          |
| Another customer's documents                                   | `403`                                                                      | `oneCustomerCannotUploadForOrReadAnother`            |
| A reviewer                                                     | Reads any customer, uploads for none                                       | `aReviewerReadsAnyCustomerButUploadsForNone`         |
| Backslashes, .htaccess, .., script tags, 300 characters, a NUL | Harmless labels; every file inside the customer's folder                   | `maliciousFileNamesBecomeHarmlessLabels`             |

## The trap

Plausible but wrong

Trusting the file name and Content-Type, and loading whole files into memory.

- **The old code's path.** The test runs `uploads.resolve(file.getOriginalFilename())` with `../../escaped.pdf`: the file lands two folders up. The program inside is "application/pdf", by the client's word.
- **The API.** The same name: the file is in the customer's folder as a UUID, the name only a label. The same program: `415`.
- **Memory.** `getBytes()` holds an upload whole. Here the server's limit refuses big uploads first, parts above 64 KB go to a temporary file, and the copy is 8 KB at a time with a limit of its own.

While building, each part was undone once: the client's name as the path turned 3 tests red; no byte check 3; no server limit 1; no copy limit 1; the full name kept as the label 2; leading dots kept 1; no owner check on upload 1; anyone may list 1; empty files accepted 1.

``` code
package com.tijori.kyc;

import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockMultipartFile;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Written first. The old upload did Files.write(uploads.resolve(file.getOriginalFilename()), file.getBytes()) and
 * accepted whatever Content-Type the client sent: a name with ../ wrote outside the folder, a program sent as
 * application/pdf was stored as a PDF, and getBytes() held every upload whole in memory.
 */
class TrustedFileNameTrapTest extends ApiTest {

    @Test
    void theOldWayWroteOutsideTheFolderAndTrustedTheHeader() throws Exception {
        Path uploads = Files.createDirectories(Path.of("target/test-storage/old/uploads/1")).toRealPath();
        MockMultipartFile file = new MockMultipartFile("file", "../../escaped.pdf", "application/pdf", EXE);
        Path target = uploads.resolve(file.getOriginalFilename()).normalize();
        Files.write(target, file.getBytes());
        assertThat(target).exists();
        assertThat(target.startsWith(uploads)).isFalse();             // written two folders up
        assertThat(file.getContentType()).isEqualTo("application/pdf");   // and "a PDF", by the client's word
        Files.delete(target);
    }

    @Test
    void theApiKeepsEveryFileInsideItsFolderUnderItsOwnName() throws Exception {
        upload("asha", 1, "PAN", "../../escaped.pdf", "application/pdf", PDF).andExpect(status().isCreated())
                .andExpect(jsonPath("$.fileName").value("escaped.pdf"));
        Path customerDir = store.root().resolve("1");
        try (var files = Files.list(customerDir)) {
            assertThat(files.map(p -> p.getFileName().toString()).toList()).singleElement().asString().matches("[0-9a-f-]{36}");
        }
        assertThat(store.root().getParent().getParent().resolve("escaped.pdf")).doesNotExist();
    }

    @Test
    void theApiDecidesTheTypeFromTheBytes() throws Exception {
        upload("asha", 1, "PAN", "pan.pdf", "application/pdf", EXE).andExpect(status().isUnsupportedMediaType())
                .andExpect(jsonPath("$.detail").value("Only PDF, PNG and JPEG documents are accepted"));
        assertThat(store.list(1)).isEmpty();
        assertThat(Files.exists(store.root().resolve("1")) ? filesUnder(store.root().resolve("1")) : 0).isZero();
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
./mvnw spring-boot:run      # the API on http://localhost:8080; files in a tijori-kyc folder under your temp folder
./mvnw test                 # all 12 tests
```

**Windows (PowerShell)**

``` code
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Rename any program or zip file to `pan.pdf` and upload it as Asha:

``` code
curl -u asha:asha-demo-pass -F type=PAN -F 'file=@pan.pdf;type=application/pdf' http://localhost:8080/kyc/1/documents
```

It answers `415`, as in case 2 (which `docs/capture.sh` sends with a file starting `MZ`). A real PDF of up to 5 MB gives `201`.

## Troubleshooting

| You see                                             | Cause                                                                        | Fix                                                                  |
|-----------------------------------------------------|------------------------------------------------------------------------------|----------------------------------------------------------------------|
| Size limits work with curl but not in MockMvc tests | MockMvc does not apply multipart limits; Tomcat does.                        | Test sizes against a real port, as `UploadSizeTest` does.            |
| A client sees a closed connection instead of 413    | Far over the limit, Tomcat answers and stops reading (2 MB more by default). | Expected; clients that read early responses, like curl, see the 413. |
| `OutOfMemoryError` on uploads                       | `getBytes()` or `readAllBytes()` on an upload.                               | Stream it (`getInputStream()`), with a limit.                        |

## Project layout

``` tree
stations/092-kyc-document-upload/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/tijori/kyc/
│   ├── SecurityConfig.java   ├── KycController.java   ├── DocumentStore.java
│   └── ProblemResponses.java   └── KycApplication.java
├── src/main/resources/application.yaml
├── src/test/java/com/tijori/kyc/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels.

#### `src/main/java/com/tijori/kyc/SecurityConfig.java`

Does  
Who may call what.

Why  
HTTP Basic; customers upload and list; reviewers list; everything else refused.

Without it  
Anyone uploading for anyone.

#### `src/main/java/com/tijori/kyc/KycController.java`

Does  
The two endpoints.

Why  
The signed-in customer must be the path's customer; the file part's stream is handed to the store; the client's name and type header are passed along only as a label.

Without it  
One customer's documents in another's hands.

#### `src/main/java/com/tijori/kyc/DocumentStore.java`

Does  
Storing a document safely.

Why  
Reads the first bytes to decide the type, streams to `root/customer/UUID` in 8 KB pieces with a 5 MB limit, hashes on the way, and cleans up the name for display.

Without it  
Path traversal, disguised programs and out-of-memory crashes.

- `BufferedInputStream.mark/reset` lets the type check read the first bytes and give them back.
- The copy's own limit is a second line: the server's multipart limit refuses big uploads first. Found while building: with the second line in place, removing the first changed no test until the size test checked where the 413 comes from.
- The list of documents is in memory, marked with a `shortcut:` comment.

#### `src/main/java/com/tijori/kyc/ProblemResponses.java`

`401` and `403` in the same problem shape as other errors.

#### `src/main/resources/application.yaml`

Does  
The limits.

Why  
`max-file-size: 5MB`, `max-request-size: 6MB`, parts above 64 KB to disk while they arrive, the storage folder.

Without it  
Unlimited uploads.

#### `src/main/java/com/tijori/kyc/KycApplication.java`

Entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                                       | Test class                                  | Result |
|---------------|-------------------------------------------------------------------|---------------------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found                          | `KycContractTest` (3), `UploadSizeTest` (2) | pass   |
| Every station | Reproduce the failure before the fix                              | `TrustedFileNameTrapTest` (3)               | pass   |
| Security      | 401, 403, one user accessing another user's data, malicious input | `KycSecurityTest` (4)                       | pass   |

`UploadSizeTest` starts the app on a real port, because MockMvc never applies multipart limits. Its 60 MB case accepts either a `413` or a closed connection, and checks that nothing was stored: Tomcat closes the connection when an upload is far over the limit, and Java's HttpClient, still sending, saw the close where curl reads the `413`. Found while building.

## Run output

JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.tijori.kyc.KycContractTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.tijori.kyc.TrustedFileNameTrapTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.tijori.kyc.UploadSizeTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.tijori.kyc.KycSecurityTest
[INFO] Tests run: 12, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/tijori/kyc/TrustedFileNameTrapTest.java`

Written first: the old path and header against the API.

#### `src/test/java/com/tijori/kyc/UploadSizeTest.java`

Sizes on a real port; the copy limit with a 64 MB stream made up as it is read.

#### `src/test/java/com/tijori/kyc/KycContractTest.java`

Uploads and lists through HTTP; bad uploads.

#### `src/test/java/com/tijori/kyc/KycSecurityTest.java`

401, 403, the reviewer, malicious file names.

#### `src/test/java/com/tijori/kyc/ApiTest.java`

Shared setup: an empty storage folder before each test, sample files by their first bytes, request helpers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/tijori/kyc/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=DownloadChallengeTest`.
3.  Change the code until it passes, then run `./mvnw test` to check the other 12 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 16 tests pass (12 station tests and 4 challenge tests).

Challenge 1 · Beginner-friendly · about 25 minutes

## Download, safely

`GET /kyc/{customerId}/documents/{documentId}/content`: the file with its detected type, as an attachment with its cleaned-up name. Owner and reviewers only; unknown documents `404`.

**Done when:** both tests in `DownloadChallengeTest` pass.

Hints

- Find the document by id in the customer's list; never build a path from the id the client sends.
- `ContentDisposition.attachment().filename(...)`; Spring Security already sends `X-Content-Type-Options: nosniff`.

#### `challenge/DownloadChallengeTest.java`

``` code
package com.tijori.kyc;

import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: GET /kyc/{customerId}/documents/{documentId}/content downloads a document: the detected type, as an
 * attachment with its cleaned-up name, never shown inline. The owner and reviewers may; others 403; unknown 404.
 */
class DownloadChallengeTest extends ApiTest {

    ResultActions download(String user, long customer, String id) throws Exception {
        return mvc.perform(get("/kyc/{c}/documents/{d}/content", customer, id).with(httpBasic(user, password(user))));
    }

    @Test
    void theOwnerAndAReviewerDownloadItAsAnAttachment() throws Exception {
        upload("asha", 1, "PAN", "../../pan card.pdf", "image/png", PDF);
        String id = store.list(1).getFirst().id();
        download("asha", 1, id).andExpect(status().isOk()).andExpect(content().contentType("application/pdf")).andExpect(content().bytes(PDF))
                .andExpect(header().string("Content-Disposition", "attachment; filename=\"pan_card.pdf\""))
                .andExpect(header().string("X-Content-Type-Options", "nosniff"));
        download("kavya", 1, id).andExpect(status().isOk());
    }

    @Test
    void othersAre403AndUnknownDocumentsAre404() throws Exception {
        upload("asha", 1, "PAN", "pan.pdf", "application/pdf", PDF);
        String id = store.list(1).getFirst().id();
        download("rohan", 1, id).andExpect(status().isForbidden());
        download("rohan", 2, id).andExpect(status().isNotFound());   // Asha's document through Rohan's own path
        download("asha", 1, "00000000-0000-0000-0000-000000000000").andExpect(status().isNotFound());
        download("asha", 1, "..%2F..%2Fetc%2Fpasswd").andExpect(status().is4xxClientError());   // refused (400) before any lookup
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 30 minutes

## The same file twice

An app retries an upload that timed out. The same bytes for the same customer and type are one document: `200` with the one already there. Other bytes or another type are new.

**Done when:** both tests in `SameFileTwiceChallengeTest` pass.

Hints

- The SHA-256 is known only after streaming: store, then compare, then delete the repeat.
- Two retries at once could both pass the check: guard the compare-and-add.

#### `challenge/SameFileTwiceChallengeTest.java`

``` code
package com.tijori.kyc;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: the app retries an upload that timed out. The same bytes for the same customer and type are not
 * stored again: 200 with the document already there (same id). Different bytes, or another type, are a new document.
 */
class SameFileTwiceChallengeTest extends ApiTest {

    @Test
    void theSameBytesAreOneDocument() throws Exception {
        String first = upload("asha", 1, "PAN", "pan.pdf", "application/pdf", PDF).andExpect(status().isCreated()).andReturn().getResponse().getContentAsString();
        String again = upload("asha", 1, "PAN", "pan-again.pdf", "application/pdf", PDF).andExpect(status().isOk()).andReturn().getResponse().getContentAsString();
        assertThat(again).isEqualTo(first);
        assertThat(filesUnder(store.root().resolve("1"))).isOne();
    }

    @Test
    void otherBytesOrAnotherTypeAreNewDocuments() throws Exception {
        upload("asha", 1, "PAN", "pan.pdf", "application/pdf", PDF).andExpect(status().isCreated());
        upload("asha", 1, "PASSPORT", "pan.pdf", "application/pdf", PDF).andExpect(status().isCreated());
        upload("asha", 1, "PAN", "pan.png", "image/png", PNG).andExpect(status().isCreated()).andExpect(jsonPath("$.contentType").value("image/png"));
        assertThat(store.list(1)).hasSize(3);
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Straight to object storage, and scanning

Move uploads off the API servers: the app asks for a pre-signed upload URL and sends the file straight to object storage. What limits can you still enforce (size, type, how long the URL works), and how does the API learn the upload finished? Where would a virus scan run, and what does a customer see while it does?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: the old path and header.
2.  Set the multipart limits; test them on a real port.
3.  Read the first bytes for the type; stream to a server-made name with a limit and a hash.
4.  Clean the client's name into a label; check owner and reviewer access.

## Design alternatives and trade-offs

| Approach                                         | What it costs                                                                                       | Verdict                |
|--------------------------------------------------|-----------------------------------------------------------------------------------------------------|------------------------|
| Server limits, byte check, stream to a UUID name | A small amount of careful code.                                                                     | Chosen                 |
| getBytes() and the client's file name            | Out of memory; files written anywhere.                                                              | The trap               |
| Path.of(name).getFileName()                      | Blocks ../, but two uploads with one name overwrite each other, and odd names still reach the disk. | Review finding         |
| Type by extension or Content-Type                | Trivial to fake.                                                                                    | Review finding         |
| Pre-signed uploads to object storage             | No bytes through the API; checks move to after the upload.                                          | At scale (challenge 3) |

## Database design

This station has no database: the list of documents is in memory (a `shortcut:` comment says so) and files are in a folder. In production, a documents table would hold the same fields, with the storage key generated by the server and a unique (customer, type, sha256) for challenge 2.

# 3 · Go deeper: Production

Limits at every hop  
The load balancer, the server and the app should all limit body size; the smallest wins, so set them on purpose.

Scanning  
Type checks are not virus checks. Scan KYC documents before anyone opens them.

Privacy  
KYC documents are personal data: encrypt them at rest, log access, and delete them when the law and the purpose allow.

Temporary files  
Multipart parts above the threshold sit in the server's temp folder while they arrive; give it space and clean-up.

# 3 · Go deeper: Interview

## Interview takeaways

How do you stop a 2 GB upload?

With the server's multipart limits, which refuse it before the application reads it, plus a limit while streaming as a second line. Test it on a real server: MockMvc does not apply them.

Why not trust the file name?

It is text from the client: ../ climbs out of folders, and names collide. Store under a name you generate; keep the client's name only as a cleaned-up label.

How do you know a file's type?

From its first bytes (magic numbers). The extension and the Content-Type header are the sender's claim.

What does streaming an upload mean?

Copying it in small pieces from the request to storage, never holding it whole in memory.

What does nosniff do?

X-Content-Type-Options: nosniff tells browsers not to guess a type from the content, so a download marked as a PDF is not run as something else.

## Self-check rubric

| Area            | Meets the bar      | Above the bar                                           |
|-----------------|--------------------|---------------------------------------------------------|
| Correctness     | All 12 tests pass. | You ran the flawed version and explained each failure.  |
| Size            | A limit is set.    | Tested on a real port; a second limit while streaming.  |
| Names and types | No ../ in paths.   | No client text in paths at all; type from bytes.        |
| Access          | 401 and 403.       | Owner and reviewer rules, and a 404 that leaks nothing. |

# 3 · Go deeper: Review

## The pull request

A teammate makes stored files easier for support: each is saved under the customer's own file name ("getFileName() takes care of ../"), and the type comes from the extension instead of the first bytes. Read the file and list every problem before opening the findings.

#### `review/DocumentStore.java`

``` code
package com.tijori.kyc;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.stereotype.Component;
import org.springframework.web.ErrorResponseException;

import java.io.BufferedInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.DigestInputStream;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.Arrays;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;

/**
 * Stores uploaded documents on disk under names the server makes up, never the client's. The bytes are streamed
 * from the request to the file in small pieces, counted and hashed on the way, and the first bytes decide the type.
 */
@Component
class DocumentStore {

    static final long MAX_BYTES = 5L * 1024 * 1024;

    record Document(String id, long customerId, String type, String fileName, String contentType, long sizeBytes, String sha256, Instant uploadedAt) {
    }

    /** Only these types are accepted, recognised by their first bytes ("magic numbers"), not by name or header. */
    private static final Map<String, byte[]> SIGNATURES = Map.of(
            "application/pdf", "%PDF-".getBytes(),
            "image/png", new byte[]{(byte) 0x89, 'P', 'N', 'G', 0x0D, 0x0A, 0x1A, 0x0A},
            "image/jpeg", new byte[]{(byte) 0xFF, (byte) 0xD8, (byte) 0xFF});

    private final Path root;
    // shortcut: the list of documents is kept in memory and lost on restart; a real service keeps it in a table.
    private final Map<Long, List<Document>> byCustomer = new ConcurrentHashMap<>();

    DocumentStore(@Value("${tijori.storage-dir}") Path root) throws IOException {
        this.root = Files.createDirectories(root).toRealPath();
    }

    Document store(long customerId, String type, String clientFileName, InputStream body) throws IOException {
        BufferedInputStream in = new BufferedInputStream(body);
        String contentType = byExtension(clientFileName);
        String id = UUID.randomUUID().toString();
        Path dir = Files.createDirectories(root.resolve(Long.toString(customerId)));
        // Keep the customer's own file name, so support can find "pan-card.pdf". getFileName() drops any ../ part.
        Path file = dir.resolve(Path.of(clientFileName).getFileName().toString());
        MessageDigest sha;
        try {
            sha = MessageDigest.getInstance("SHA-256");
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
        long size;
        try (InputStream digesting = new DigestInputStream(in, sha); OutputStream out = Files.newOutputStream(file)) {
            size = copyAtMost(digesting, out, MAX_BYTES);
        } catch (TooLarge e) {
            Files.deleteIfExists(file);
            throw problem(HttpStatus.CONTENT_TOO_LARGE, "A document can be at most 5 MB");
        }
        Document d = new Document(id, customerId, type, displayName(clientFileName), contentType, size, HexFormat.of().formatHex(sha.digest()), Instant.now());
        byCustomer.computeIfAbsent(customerId, c -> new CopyOnWriteArrayList<>()).add(d);
        return d;
    }

    List<Document> list(long customerId) {
        return List.copyOf(byCustomer.getOrDefault(customerId, List.of()));
    }

    Path root() {
        return root;
    }

    /** For tests: forget all documents. */
    void clear() {
        byCustomer.clear();
    }

    /** The extension says what the file is; checking the bytes as well is slow and fiddly. */
    static String byExtension(String name) {
        String n = name.toLowerCase(java.util.Locale.ROOT);
        if (n.endsWith(".pdf")) {
            return "application/pdf";
        }
        if (n.endsWith(".png")) {
            return "image/png";
        }
        if (n.endsWith(".jpg") || n.endsWith(".jpeg")) {
            return "image/jpeg";
        }
        throw problem(HttpStatus.UNSUPPORTED_MEDIA_TYPE, "Only PDF, PNG and JPEG documents are accepted");
    }

    /** Looks at the first bytes without consuming them. */
    static String sniff(BufferedInputStream in) throws IOException {
        in.mark(16);
        byte[] head = in.readNBytes(8);
        in.reset();
        if (head.length == 0) {
            throw problem(HttpStatus.BAD_REQUEST, "The file is empty");
        }
        return SIGNATURES.entrySet().stream()
                .filter(s -> head.length >= s.getValue().length && Arrays.equals(Arrays.copyOf(head, s.getValue().length), s.getValue()))
                .map(Map.Entry::getKey).findFirst()
                .orElseThrow(() -> problem(HttpStatus.UNSUPPORTED_MEDIA_TYPE, "Only PDF, PNG and JPEG documents are accepted"));
    }

    /** Copies in 8 KB pieces and stops as soon as the limit is passed, without reading the rest. */
    static long copyAtMost(InputStream in, OutputStream out, long limit) throws IOException {
        byte[] buffer = new byte[8192];
        long total = 0;
        for (int n; (n = in.read(buffer)) != -1; ) {
            total += n;
            if (total > limit) {
                throw new TooLarge();
            }
            out.write(buffer, 0, n);
        }
        return total;
    }

    /** The client's name is shown, never used as a path: the last part only, safe characters, at most 100. */
    static String displayName(String clientFileName) {
        if (clientFileName == null) {
            return "document";
        }
        String last = clientFileName.substring(Math.max(clientFileName.lastIndexOf('/'), clientFileName.lastIndexOf('\\')) + 1);
        String safe = last.replaceAll("[^A-Za-z0-9._-]", "_");
        safe = safe.replaceAll("^\\.+", "");   // no hidden or "..": a name is never a directory
        return safe.isEmpty() ? "document" : safe.substring(0, Math.min(100, safe.length()));
    }

    static ErrorResponseException problem(HttpStatus status, String detail) {
        return new ErrorResponseException(status, ProblemDetail.forStatusAndDetail(status, detail), null);
    }

    static final class TooLarge extends RuntimeException {
    }
}
```

## Findings

1The customer's file name as the stored name

"So support can find pan-card.pdf": `getFileName()` drops `../`, but a second upload with the same name overwrites the first, the name `..` resolves to the folder itself, and every odd character reaches the disk.

**Test evidence:** `theApiKeepsEveryFileInsideItsFolderUnderItsOwnName`, `aDocumentIsStoredWithItsDetectedTypeSizeAndHash` and `maliciousFileNamesBecomeHarmlessLabels` fail.

2The type from the extension

"Checking the bytes is slow and fiddly": a program named `pan.pdf` is now a PDF, an empty `.pdf` is accepted, a real PNG named `.pdf` is called a PDF, and a JPEG with no extension is refused.

**Test evidence:** `theApiDecidesTheTypeFromTheBytes`, `theTypeComesFromTheBytesNotTheHeader` and `badUploadsAre400AndUnknownCustomersAre404` fail.

## Same tests, flawed version

From `docs/review-run.txt`: the flawed file copied over the real one, then the full suite run.

| Test class                | Fixed version | Flawed version |
|---------------------------|---------------|----------------|
| `UploadSizeTest`          | 2 / 2         | 2 / 2          |
| `KycContractTest`         | 3 / 3         | 0 / 3          |
| `KycSecurityTest`         | 4 / 4         | 3 / 4          |
| `TrustedFileNameTrapTest` | 3 / 3         | 1 / 3          |

The size limits are untouched, and an honest customer uploading pan-card.pdf sees no difference. Every failure needs a name or a file someone chose to be odd.
