# Station 097 · Behind a load balancer

Working Systems · 0–2 years · Core · SaaS · Types: Security

Spring Boot 4.1.1 · Java 25 · Tomcat RemoteIpValve (server.forward-headers-strategy=native) · X-Forwarded-For / -Proto / -Host · trusted proxies · Tomcat timeouts · Spring Security 7 · stateless sessions. Needs JDK 25 (or 21, see Set up & code). No Docker, no database. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows). The tests use the loopback addresses 127.0.0.1 (the load balancer) and 127.0.0.2 (a client), which Linux and Windows route by default; on macOS add 127.0.0.2 first (`sudo ifconfig lo0 alias 127.0.0.2`).

**Simulation:** Uploads are simulated storage: each one is read to the end, counted and hashed, and the bytes are not kept. The load balancer in the captures is a small Python script (docs/test-balancer.py); the addresses are documentation ranges.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 12 tests.

# 1 · Understand

## The problem in real life

1.  **One address for everyone**

    Mapwise put a load balancer in front of the API. Now every request seemed to come from the balancer's address, links pointed to `http://10.0.0.17:8080/`, and big uploads timed out.

2.  **A quick fix, a new hole**

    A teammate read the client's address from X-Forwarded-For. But anyone can send that header: a user at home wrote the office's address into it and opened the admin page.

3.  **The fix**

    Tomcat rewrites the address, scheme and host from X-Forwarded-\*, only for requests that really come from the balancer, and only from the balancer's own entry. Every hop has a timeout, and the app keeps no session.

A header is only as trustworthy as whoever wrote it. Believe X-Forwarded-For from your balancer, never from the client.

## What are we building?

An API that knows the real client, the real scheme and the public host name behind a load balancer, without letting any client choose them.

## An everyday analogy

A receptionist writes "from: Mrs Rao, front door" on each visitor's slip. The clerk believes slips the receptionist wrote, and ignores the ones visitors wrote themselves.

## How it works in 4 steps

1.  **The balancer adds** the client's address to the end of X-Forwarded-For, and the scheme and host it was asked for.
2.  **Tomcat checks** who is talking: the balancer's address, or someone else? Anyone else: the headers are ignored.
3.  **Tomcat reads from the right**: the last entry is the one the balancer wrote; anything before it the client could have written.
4.  **The app uses** the request as rewritten: the real client for the office check, https and the public name for links.

Check yourself: the balancer receives `X-Forwarded-For: 203.0.113.9` from a client at 198.51.100.7. What does it send on, and which address is the client?

`203.0.113.9, 198.51.100.7`. The client is 198.51.100.7: the balancer wrote that one. The first entry is whatever the client typed.

## What this station is not

- **No real balancer.** Tests send its headers from 127.0.0.1; the captures use a Python one.
- **No TLS here.** The balancer ends https; the app speaks http behind it.
- **No real storage.** Uploads are counted and hashed, not kept.

## Key terms

| Term                          | Simple meaning                                                                            | Everyday example                                                 | In this project                 |
|-------------------------------|-------------------------------------------------------------------------------------------|------------------------------------------------------------------|---------------------------------|
| **Load balancer**             | A server in front of yours that spreads requests over several copies of your app.         | A receptionist sending visitors to free counters.                | 10.0.0.0/24                     |
| **X-Forwarded-For**           | A header where proxies write the address of whoever sent them the request.                | A note "from: Mrs Rao" on a parcel the receptionist hands on.    | `203.0.113.9, 198.51.100.7`     |
| **X-Forwarded-Proto / -Host** | Whether the client used https, and which name it typed.                                   | "She came in by the front door, asking for Mapwise".             | `https`, `maps.mapwise.example` |
| **Trusted proxy**             | A machine whose X-Forwarded-\* headers you believe: your balancer, nobody else.           | Believing the receptionist's note, not a note the visitor wrote. | `internal-proxies`              |
| **Timeout**                   | How long one side waits for the other before giving up.                                   | How long a counter waits for a visitor who stepped away.         | 20 s, 75 s, 60 s                |
| **Sticky session**            | The balancer sending a user always to the same server because that server remembers them. | Always the same counter, because only that clerk has your file.  | Not needed here                 |

# 2 · Build: Spec

## Business problem

**Mapwise** (a fictional maps company): behind the load balancer every request seems to come from one IP, redirects point to `http://`, and uploads time out at 60 seconds.

## Acceptance criteria

Demo rules: the balancer is 10.0.0.0/24; the office is 203.0.113.0/24; uploads at most 10 MiB. Users asha and vikram, admin ops; password: the name plus `-demo-pass`.

1.  **Given** a request through the balancer, **then** the app sees the client's address, `https`, the public host and port 443.
2.  **Given** a client that writes its own X-Forwarded-For, **then** it is ignored (direct) or only the balancer's entry counts (through it).
3.  **Given** an upload, **then** `201` with `Location: https://maps.mapwise.example/uploads/{id}`; over the limit `413`.
4.  **Given** a client that stops sending in the middle of an upload, **then** the app answers `408` after its read timeout and stores nothing.
5.  **Given** `/admin/uploads`, **then** only an admin from the office: anyone else `403`, no sign-in `401`; another user's upload `404`.

## Requirements

- Only the balancer's addresses are trusted, not Spring Boot's default list.
- No HTTP session: any copy of the app can answer any request.
- Every hop has a timeout, and the app's keep-alive outlasts the balancer's idle timeout.

## Learning objectives

- Configure forwarded headers in Tomcat with an explicit list of trusted proxies.
- Explain why X-Forwarded-For is read from the right.
- Build absolute links from the request, so they are right behind any proxy.
- Set timeouts at each hop and say which one must be longer.
- Test proxy behaviour on a real port from two different client addresses.

# 2 · Build: API contract

## Endpoints

| Method | Path             | Purpose                                                 |
|--------|------------------|---------------------------------------------------------|
| `GET`  | `/whoami`        | What the app believes about this request (public).      |
| `POST` | `/uploads`       | Upload a file as the raw body; `201` with its Location. |
| `GET`  | `/uploads/{id}`  | Your own upload.                                        |
| `GET`  | `/admin/uploads` | Every upload: admins, from the office network only.     |

## Status codes

| Status | When                                                                           |
|--------|--------------------------------------------------------------------------------|
| 200    | whoami; your upload; the admin list                                            |
| 201    | Upload stored                                                                  |
| 401    | No sign-in, or a wrong password                                                |
| 403    | The admin list: not an admin, or not from the office                           |
| 404    | No such upload, or another user's                                              |
| 408    | The client stopped sending before the upload was complete (answered by Tomcat) |
| 413    | Over 10 MiB                                                                    |

## Captured examples

Captured with curl from 127.0.0.2 on 23 Oct 2026, in this order. Port 8080 is the app as configured (its balancer is 10.0.0.0/24, so curl is just a client). Port 8081 is `docs/test-balancer.py`, a small Python balancer, in front of a second copy of the app that trusts it. `Date`, connection and standard security headers are left out.

### Case 1: straight to the app

**Why:** the client is who connected: 127.0.0.2, plain http.

Request

``` code
GET /whoami HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 123

{
  "clientIp": "127.0.0.2",
  "scheme": "http",
  "secure": false,
  "host": "127.0.0.1",
  "port": 8080,
  "url": "http://127.0.0.1:8080/whoami"
}
```

### Case 2: straight, with a made-up X-Forwarded-For

**Why:** ignored: 127.0.0.2 is not the balancer.

Request

``` code
GET /whoami HTTP/1.1
X-Forwarded-For: 203.0.113.9
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 123

{
  "clientIp": "127.0.0.2",
  "scheme": "http",
  "secure": false,
  "host": "127.0.0.1",
  "port": 8080,
  "url": "http://127.0.0.1:8080/whoami"
}
```

### Case 3: the admin pretends to be in the office

**Why:** `403`: the office check sees 127.0.0.2.

Request

``` code
GET /admin/uploads HTTP/1.1
Authorization: Basic b3BzOm9wcy1kZW1vLXBhc3M=
X-Forwarded-For: 203.0.113.9
```

Response

``` code
HTTP/1.1 403 
Content-Type: application/problem+json
Content-Length: 104

{
  "title": "Not allowed",
  "status": 403,
  "detail": "This sign-in cannot do this.",
  "instance": "/admin/uploads"
}
```

### Case 4: through the balancer

**Why:** the balancer's entry is the client; https, the public name, port 443. Spring Security now knows the request is https and adds `Strict-Transport-Security`; the `Server` header is the Python balancer's.

Request

``` code
GET /whoami HTTP/1.1
```

Response

``` code
HTTP/1.1 200 OK
Server: BaseHTTP/0.6 Python/3.13.16
Strict-Transport-Security: max-age=31536000 ; includeSubDomains
Content-Type: application/json
Content-Length: 140

{
  "clientIp": "127.0.0.2",
  "scheme": "https",
  "secure": true,
  "host": "maps.mapwise.example",
  "port": 443,
  "url": "https://maps.mapwise.example/whoami"
}
```

### Case 5: through the balancer, with a made-up header

**Why:** the balancer appended 127.0.0.2 after the made-up 203.0.113.9; Tomcat reads from the right and takes 127.0.0.2.

Request

``` code
GET /whoami HTTP/1.1
X-Forwarded-For: 203.0.113.9
```

Response

``` code
HTTP/1.1 200 OK
Server: BaseHTTP/0.6 Python/3.13.16
Strict-Transport-Security: max-age=31536000 ; includeSubDomains
Content-Type: application/json
Content-Length: 140

{
  "clientIp": "127.0.0.2",
  "scheme": "https",
  "secure": true,
  "host": "maps.mapwise.example",
  "port": 443,
  "url": "https://maps.mapwise.example/whoami"
}
```

### Case 6: Asha uploads

**Why:** `201`; the Location is the public https address, not the app's own.

Request

``` code
POST /uploads HTTP/1.1
Authorization: Basic YXNoYTphc2hhLWRlbW8tcGFzcw==
Content-Type: application/octet-stream

quarterly-report-v3
```

Response

``` code
HTTP/1.1 201 Created
Server: BaseHTTP/0.6 Python/3.13.16
Location: https://maps.mapwise.example/uploads/1
Strict-Transport-Security: max-age=31536000 ; includeSubDomains
Content-Type: application/json
Content-Length: 133

{
  "id": 1,
  "owner": "asha",
  "bytes": 19,
  "sha256": "57692f2b65bf53aaf7225a41f624b3e1d2ecd2cfee939216ccbe990684e9d669",
  "clientIp": "127.0.0.2"
}
```

### Case 7: the admin, through the balancer, from outside the office

**Why:** `403`.

Request

``` code
GET /admin/uploads HTTP/1.1
Authorization: Basic b3BzOm9wcy1kZW1vLXBhc3M=
```

Response

``` code
HTTP/1.1 403 Forbidden
Server: BaseHTTP/0.6 Python/3.13.16
Strict-Transport-Security: max-age=31536000 ; includeSubDomains
Content-Type: application/problem+json
Content-Length: 104

{
  "title": "Not allowed",
  "status": 403,
  "detail": "This sign-in cannot do this.",
  "instance": "/admin/uploads"
}
```

### Case 8: no sign-in

**Why:** `401`.

Request

``` code
POST /uploads HTTP/1.1
Content-Type: application/octet-stream

x
```

Response

``` code
HTTP/1.1 401 Unauthorized
Server: BaseHTTP/0.6 Python/3.13.16
WWW-Authenticate: Basic realm="mapwise"
Strict-Transport-Security: max-age=31536000 ; includeSubDomains
Content-Type: application/problem+json
Content-Length: 110

{
  "title": "Sign-in required",
  "status": 401,
  "detail": "Send a valid username and password.",
  "instance": "/uploads"
}
```

### Case 9: Vikram reads Asha's upload

**Why:** `404`, the same as one that does not exist.

Request

``` code
GET /uploads/1 HTTP/1.1
Authorization: Basic dmlrcmFtOnZpa3JhbS1kZW1vLXBhc3M=
```

Response

``` code
HTTP/1.1 404 Not Found
Server: BaseHTTP/0.6 Python/3.13.16
Strict-Transport-Security: max-age=31536000 ; includeSubDomains
Content-Type: application/problem+json
Content-Length: 85

{
  "detail": "No such upload.",
  "instance": "/uploads/1",
  "status": 404,
  "title": "Not Found"
}
```

## A stalled upload

From `docs/capture.sh`, against port 8080 and its 20 s read timeout:

``` code
sent 10 of 1,000 bytes, then nothing; after 20 s (rounded down) the app answered: HTTP/1.1 408
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                                             | What happens                                        | Proved by                                                     |
|----------------------------------------------------------------------------------|-----------------------------------------------------|---------------------------------------------------------------|
| The old way, straight or through the balancer                                    | The office address the client wrote                 | `theOldWayBelievesWhateverTheClientWrites`                    |
| The API, straight or through the balancer                                        | 127.0.0.2; the balancer's entry; `403`              | `theApiTrustsTheHeaderOnlyFromTheBalancerAndOnlyItsLastEntry` |
| Boot's default trusted list, a machine that is not the balancer                  | Believed: `200` on /admin                           | `withBootsDefaultListAMachineInsideTheNetworkCanBeTheOffice`  |
| A direct request                                                                 | Taken as it is                                      | `aDirectRequestIsTakenAsItIs`                                 |
| Through the balancer                                                             | Client, https, public host, port 443                | `throughTheBalancerTheAppSeesTheClientHttpsAndThePublicName`  |
| An upload; one byte over the limit; an unknown id                                | `201` with an https Location; `413`; `404`          | `anUploadIsCountedAndItsLocationIsThePublicHttpsAddress`      |
| An upload that stops half way                                                    | `408` after the read timeout; nothing stored        | `aStalledUploadIsCutOffAndNothingIsStored`                    |
| Any signed-in request                                                            | No session cookie                                   | `noSessionCookieSoNoStickySessionsAreNeeded`                  |
| No sign-in, a wrong password                                                     | `401`                                               | `withoutASignInUploadsAre401`                                 |
| Admin from home; a user from the office                                          | `403`                                               | `theAdminListIsForAdminsInTheOfficeOnly`                      |
| Another user's upload                                                            | `404`                                               | `aUserCannotReadAnotherUsersUpload`                           |
| Not an address, a look-alike name, a made-up protocol, two headers, 50 fake hops | Never the office, never https, the balancer's entry | `maliciousForwardedHeadersGiveNothingAway`                    |

## The trap

Plausible but wrong

Trusting X-Forwarded-For from anyone, so clients can spoof their IP.

- **The old way.** "The first address in X-Forwarded-For is the client": for a client that wrote `203.0.113.9` itself, straight to the app or through the balancer, that is the office.
- **The API.** The same requests: straight to the app the header is ignored (the client is 127.0.0.2, `403`); through the balancer the last entry, the one the balancer wrote, is the client.
- **The second half.** Forward headers on, but Spring Boot's default list of trusted proxies: every private and loopback range. A machine that is not the balancer, at 127.0.0.2, is trusted, and its made-up office address opens `/admin`.

While building, each part was undone once: forward headers off turned 6 tests red; no office check 3; no admin check 2; any user's upload 1; a fixed `http://localhost:8080` link 1; no upload limit 1; sessions on 1. Removing the header names (`remote-ip-header`, `protocol-header`, `host-header`) turned nothing red: they were Boot's defaults, so they were deleted. A catch that turned a stalled read into our own `408` never ran (Tomcat answers 408 itself), so it was deleted too.

``` code
package com.mapwise.edge;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/** A client outside the office writes the office's address into X-Forwarded-For. Written first. */
class SpoofedClientIpTrapTest extends ApiTest {

    /** The old way: the first address in X-Forwarded-For is the client. Whoever sent the header. */
    static String oldClientIp(String forwardedFor, String remoteAddr) {
        return forwardedFor == null ? remoteAddr : forwardedFor.split(",")[0].strip();
    }

    @Test
    void theOldWayBelievesWhateverTheClientWrites() {
        // Straight to the app, and through the balancer (which appends the real address): the old way sees the office both times.
        assertThat(oldClientIp("203.0.113.9", DIRECT)).isEqualTo("203.0.113.9");
        assertThat(oldClientIp("203.0.113.9, 198.51.100.7", BALANCER)).isEqualTo("203.0.113.9");
        assertThat(SecurityConfig.fromNetwork(new org.springframework.security.web.util.matcher.IpAddressMatcher("203.0.113.0/24"), "203.0.113.9")).isTrue();
    }

    @Test
    void theApiTrustsTheHeaderOnlyFromTheBalancerAndOnlyItsLastEntry() throws Exception {
        var direct = send(DIRECT, as("ops", request("/admin/uploads")).header("X-Forwarded-For", "203.0.113.9"));
        assertThat(direct.statusCode()).isEqualTo(403);   // the header from a client is ignored: it is 127.0.0.2
        var spoofedThroughBalancer = send(BALANCER, as("ops", viaBalancer("/admin/uploads", "203.0.113.9, 198.51.100.7")));
        assertThat(spoofedThroughBalancer.statusCode()).isEqualTo(403);   // the balancer's entry, 198.51.100.7, is the client
        assertThat(json(send(BALANCER, viaBalancer("/whoami", "203.0.113.9, 198.51.100.7"))).get("clientIp").asString()).isEqualTo("198.51.100.7");
        assertThat(json(send(DIRECT, request("/whoami").header("X-Forwarded-For", "203.0.113.9"))).get("clientIp").asString()).isEqualTo(DIRECT);
    }
}
```

``` code
package com.mapwise.edge;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;

import java.net.InetAddress;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.Base64;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * The second half of the trap: forward headers on, but Spring Boot's default list of trusted proxies (every private
 * and loopback range, copied from Boot 4.1.1's own metadata). Any machine inside the network can then claim any address.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT, properties = "server.tomcat.remoteip.internal-proxies="
        + "192.168.0.0/16, 172.16.0.0/12, 169.254.0.0/16, fc00::/7, 10.0.0.0/8, 100.64.0.0/10, 127.0.0.0/8, fe80::/10, ::1/128")
class DefaultTrustedProxiesTrapTest {

    @LocalServerPort
    int port;

    @Test
    void withBootsDefaultListAMachineInsideTheNetworkCanBeTheOffice() throws Exception {
        HttpRequest request = HttpRequest.newBuilder(URI.create("http://127.0.0.1:" + port + "/admin/uploads"))
                .header("Authorization", "Basic " + Base64.getEncoder().encodeToString("ops:ops-demo-pass".getBytes()))
                .header("X-Forwarded-For", "203.0.113.9").build();
        try (HttpClient fromAnotherMachine = HttpClient.newBuilder().localAddress(InetAddress.getByName("127.0.0.2")).build()) {
            // 127.0.0.2 is not the balancer, but it is in 127.0.0.0/8: trusted, so its made-up header is believed.
            assertThat(fromAnotherMachine.send(request, HttpResponse.BodyHandlers.ofString()).statusCode()).isEqualTo(200);
        }
    }
}
```

# 2 · Build: Set up & code

## Set up and run

| You need   | Version                                                        | Check with                          |
|------------|----------------------------------------------------------------|-------------------------------------|
| JDK        | 25 (recommended). JDK 21 also works, see below                 | `java -version`                     |
| Python 3   | Only for the test balancer in Try it yourself                  | `python3 --version`                 |
| macOS only | The address 127.0.0.2 on the loopback interface, for the tests | `sudo ifconfig lo0 alias 127.0.0.2` |
| Maven      | Not needed: the project ships the Maven wrapper                |                                     |

**macOS / Linux**

``` code
./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all 12 tests
```

**Windows (PowerShell)**

``` code
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. `HttpClient.Builder.localAddress`, which the tests use, is in Java 19 and later.

## Try it yourself

Run a copy of the app that trusts this machine as its balancer, and the Python balancer in front of it:

``` code
./mvnw spring-boot:run -Dspring-boot.run.arguments='--server.port=8082 --server.tomcat.remoteip.internal-proxies=127.0.0.1/32'
python3 docs/test-balancer.py 8081 8082
curl -H 'X-Forwarded-For: 203.0.113.9' http://localhost:8081/whoami
```

The answer shows `127.0.0.1` (curl's address, appended by the balancer), `https` and `maps.mapwise.example`: your made-up address is not the client.

## Troubleshooting

| You see                                             | Cause                                                                  | Fix                                                              |
|-----------------------------------------------------|------------------------------------------------------------------------|------------------------------------------------------------------|
| Every client has the balancer's address             | Forward headers are off, or the balancer is not in `internal-proxies`. | `forward-headers-strategy: native` and the balancer's addresses. |
| Links start with `http://` behind an https balancer | The balancer does not send X-Forwarded-Proto, or it is not trusted.    | Send it; trust the balancer.                                     |
| Random 502s from the balancer                       | The app closes idle connections before the balancer does.              | App keep-alive longer than the balancer's idle timeout.          |
| Tests fail to bind 127.0.0.2 (macOS)                | macOS routes only 127.0.0.1 by default.                                | `sudo ifconfig lo0 alias 127.0.0.2`                              |

## Project layout

``` tree
stations/097-behind-a-load-balancer/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/mapwise/edge/
│   ├── SecurityConfig.java   ├── WhoAmIController.java   ├── UploadController.java
│   └── Uploads.java   ├── ProblemResponses.java   └── EdgeApplication.java
├── src/main/resources/application.yaml
├── src/test/java/com/mapwise/edge/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, the Python balancer, captures, saved runs
```

## Code walkthrough

Configuration first: most of this station is in it. Then the code, in the order a request travels.

#### `src/main/resources/application.yaml`

Does  
Where the forwarded headers are trusted, and the timeouts.

Why  
`forward-headers-strategy: native`, `internal-proxies` set to the balancer's subnet only, a 20 s read timeout and a 75 s keep-alive.

Without it  
Any machine inside the network choosing its client address; the balancer reusing a connection the app has just closed.

- Spring Boot 4.1.1's default `internal-proxies` is every private and loopback range (from Boot's own configuration metadata): convenient, and wrong for most networks.
- The header names are Boot's defaults; nothing else needs setting.

#### `src/main/java/com/mapwise/edge/SecurityConfig.java`

Does  
Who may do what.

Why  
HTTP Basic, no session; /admin only for admins whose `getRemoteAddr()` is in the office network.

Without it  
A client reaching /admin by writing a header.

#### `src/main/java/com/mapwise/edge/WhoAmIController.java`

What the request looks like after Tomcat rewrote it.

#### `src/main/java/com/mapwise/edge/UploadController.java`

Does  
Uploads.

Why  
Builds the Location from the request (`ServletUriComponentsBuilder`), so it carries https and the public host.

Without it  
Links that point at the app's internal address.

#### `src/main/java/com/mapwise/edge/Uploads.java`

Does  
Reading an upload.

Why  
8 KB at a time, counted and hashed, stopped at the limit.

Without it  
Memory that grows with the file; a stalled client holding a thread.

#### `src/main/java/com/mapwise/edge/ProblemResponses.java`

`401` and `403` in the problem shape.

#### `src/main/java/com/mapwise/edge/EdgeApplication.java`

Entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                                       | Test class                                                         | Result |
|---------------|-------------------------------------------------------------------|--------------------------------------------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found                          | `ProxyContractTest` (3), `TimeoutAndSessionTest` (2)               | pass   |
| Every station | Reproduce the failure before the fix                              | `SpoofedClientIpTrapTest` (2), `DefaultTrustedProxiesTrapTest` (1) | pass   |
| Security      | 401, 403, one user accessing another user's data, malicious input | `ProxySecurityTest` (4)                                            | pass   |

These tests need a real server: the valve that reads X-Forwarded-\* runs inside Tomcat, and MockMvc has no Tomcat. Each request is sent from a chosen address with `HttpClient.Builder.localAddress`: 127.0.0.1 plays the balancer, 127.0.0.2 a client. The tests use a 1 s read timeout and a 1 MiB upload limit so they run quickly.

Found while building: one byte over 10 MiB, the Java client saw the connection close instead of the `413`. Tomcat answers and then reads at most 2 MB more of the body before closing; a client still sending 10 MB sees the close first. With a 1 MiB limit in the tests the rest fits, and the `413` arrives.

## Run output

JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 1, Failures: 0, Errors: 0, Skipped: 0 -- in com.mapwise.edge.DefaultTrustedProxiesTrapTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.mapwise.edge.SpoofedClientIpTrapTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.mapwise.edge.TimeoutAndSessionTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.mapwise.edge.ProxyContractTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.mapwise.edge.ProxySecurityTest
[INFO] Tests run: 12, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/mapwise/edge/SpoofedClientIpTrapTest.java`

Written first: the old way against the API.

#### `src/test/java/com/mapwise/edge/DefaultTrustedProxiesTrapTest.java`

Boot's default trusted list, shown letting a non-balancer in.

#### `src/test/java/com/mapwise/edge/ProxyContractTest.java`

Direct and through the balancer; uploads and their Location.

#### `src/test/java/com/mapwise/edge/TimeoutAndSessionTest.java`

A stalled upload on a raw socket; no session cookie.

#### `src/test/java/com/mapwise/edge/ProxySecurityTest.java`

401, 403, another user's upload, malicious headers.

#### `src/test/java/com/mapwise/edge/ApiTest.java`

Shared setup: a real port, requests from a chosen address, the balancer's headers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/mapwise/edge/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=RequestIdChallengeTest`.
3.  Change the code until it passes, then run `./mvnw test` to check the other 12 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 16 tests pass (12 station tests and 4 challenge tests).

Challenge 1 · Beginner-friendly · about 25 minutes

## One id across hops

Every answer carries `X-Request-Id`, so one request can be found in the balancer's log and the app's. Keep the balancer's id; replace one a client sent itself (it could reuse another request's id to muddle the logs); make one when there is none. Errors too.

**Done when:** both tests in `RequestIdChallengeTest` pass.

Hints

- Tomcat's valve marks requests that came through a trusted proxy: the request attribute `org.apache.tomcat.request.forwarded`.
- A filter that runs before Spring Security, so `401`s get an id too.
- The id goes into logs: allow only a short, safe set of characters.

#### `challenge/RequestIdChallengeTest.java`

``` code
package com.mapwise.edge;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Challenge 1: every answer carries X-Request-Id, so one request can be followed through the balancer's log and the
 * app's. The balancer's id is kept; a client's own is not trusted (it could reuse someone else's to muddle the logs).
 */
class RequestIdChallengeTest extends ApiTest {

    static final String UUID = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}";

    @Test
    void theBalancersIdIsKept() throws Exception {
        var response = send(BALANCER, viaBalancer("/whoami", "198.51.100.7").header("X-Request-Id", "lb-7f3a9c"));
        assertThat(response.headers().firstValue("X-Request-Id")).hasValue("lb-7f3a9c");
    }

    @Test
    void aClientsOwnIdIsReplacedAndAMissingOneIsMade() throws Exception {
        var direct = send(DIRECT, request("/whoami").header("X-Request-Id", "lb-7f3a9c"));
        assertThat(direct.headers().firstValue("X-Request-Id").orElseThrow()).matches(UUID);
        var none = send(BALANCER, viaBalancer("/whoami", "198.51.100.7"));
        assertThat(none.headers().firstValue("X-Request-Id").orElseThrow()).matches(UUID);
        var unauthorised = send(BALANCER, viaBalancer("/uploads", "198.51.100.7").POST(java.net.http.HttpRequest.BodyPublishers.ofString("x")));
        assertThat(unauthorised.statusCode()).isEqualTo(401);
        assertThat(unauthorised.headers().firstValue("X-Request-Id")).isPresent();   // errors too: they are what you look up
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 35 minutes

## Three uploads a minute per client

At most 3 uploads a minute from one client address (a demo rule), `429` with `Retry-After` after that. It only works because the address is real: with the old way, a client would write a new X-Forwarded-For each time.

**Done when:** both tests in `UploadsPerClientChallengeTest` pass.

Hints

- Key the window by `getRemoteAddr()`: after the valve, that is the client.
- A deque of times per address, trimmed to the last minute, under a lock per address.

#### `challenge/UploadsPerClientChallengeTest.java`

``` code
package com.mapwise.edge;

import org.junit.jupiter.api.Test;

import java.net.http.HttpRequest;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Challenge 2: at most 3 uploads a minute from one client address (demo rule). It only works because the address is
 * the real one: with the old way, a client would write a new X-Forwarded-For each time and never be limited.
 */
class UploadsPerClientChallengeTest extends ApiTest {

    int upload(String from, HttpRequest.Builder request) throws Exception {
        return send(from, as("vikram", request).POST(HttpRequest.BodyPublishers.ofString("a file"))).statusCode();
    }

    @Test
    void theFourthUploadInAMinuteFromOneAddressIs429() throws Exception {
        for (int i = 0; i < 3; i++) {
            assertThat(upload(BALANCER, viaBalancer("/uploads", "198.51.100.20"))).isEqualTo(201);
        }
        var fourth = send(BALANCER, as("vikram", viaBalancer("/uploads", "198.51.100.20")).POST(HttpRequest.BodyPublishers.ofString("a file")));
        assertThat(fourth.statusCode()).isEqualTo(429);
        assertThat(fourth.headers().firstValue("Retry-After")).isPresent();
        assertThat(upload(BALANCER, viaBalancer("/uploads", "198.51.100.21"))).isEqualTo(201);   // another client is not affected
    }

    @Test
    void aClientCannotEscapeItsLimitWithMadeUpAddresses() throws Exception {
        for (int i = 0; i < 3; i++) {
            assertThat(upload(DIRECT, request("/uploads").header("X-Forwarded-For", "203.0.113." + i))).isEqualTo(201);
        }
        assertThat(upload(DIRECT, request("/uploads").header("X-Forwarded-For", "203.0.113.99"))).isEqualTo(429);
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## An upload longer than any timeout

Field teams upload 2 GB survey videos over slow mobile networks: 20 minutes or more, through a balancer that cuts connections after 60 s of silence and a CDN with its own limits. Design it so no hop's timeout matters: the API hands out a short-lived signed URL, the phone uploads straight to object storage in parts it can resume, and storage tells the API when it is done. Which timeouts are left, and who owns each?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap tests: the old way, and Boot's default trusted list.
2.  Turn on forward headers in Tomcat with the balancer's addresses only.
3.  Build links from the request; check the office against `getRemoteAddr()`.
4.  Set the timeouts and prove the read timeout with a stalled upload.

## Design alternatives and trade-offs

| Approach                                                | What it costs                                                                                       | Verdict                    |
|---------------------------------------------------------|-----------------------------------------------------------------------------------------------------|----------------------------|
| Tomcat's valve with an explicit list of trusted proxies | One list to keep up to date when the balancer moves.                                                | Chosen                     |
| Read X-Forwarded-For yourself, first entry              | Any client chooses its address.                                                                     | The trap                   |
| The valve with Boot's default list                      | Every private address is trusted: any machine inside can spoof.                                     | The trap, second half      |
| Spring's `ForwardedHeaderFilter` (strategy `framework`) | Trusts the headers from anyone; only safe if the app cannot be reached except through the balancer. | Only with a closed network |
| The RFC 7239 `Forwarded` header                         | One standard header instead of three; not every balancer sends it.                                  | If your balancer does      |
| Sticky sessions                                         | Uneven load; users lose their state when a server goes.                                             | Avoid: stay stateless      |

## Database design

No database: uploads are kept in memory, which is exactly what would force sticky sessions with several copies of the app. In production their records go to a database and their bytes to object storage, so any copy can answer.

# 3 · Go deeper: Production

Timeouts at every hop  
Client to balancer: the balancer's idle timeout (60 s is a common default). Balancer to app: the app's keep-alive must be longer than that, or the balancer reuses a connection the app just closed (a 502). The app's read timeout frees threads from stalled clients. App to anything it calls: a connect and a read timeout on every client, shorter than the request's own.

Close the side door  
If the app can be reached without the balancer, every header check matters more. Put it in a private network or security group that only the balancer can reach.

Several layers  
CDN, then balancer, then app: each layer appends; trust them all in `internal-proxies` or `trusted-proxies`, and nothing else.

Long uploads  
Raise the balancer's idle timeout only for upload paths, or upload straight to object storage (challenge 3).

Logs  
Log the rewritten client address, and the request id the balancer sends (challenge 1).

# 3 · Go deeper: Interview

## Interview takeaways

How does your app learn the client's IP behind a load balancer?

From X-Forwarded-For, but only when the request comes from the balancer, and from the entry the balancer appended: read it from the right, skipping trusted proxies.

Why not the first entry?

The client can send the header with anything in it; the balancer appends to it. The first entry is whatever the client wrote.

Why do links say http:// behind an https balancer?

The app sees plain http from the balancer. Trust X-Forwarded-Proto from it, and build links from the request.

Which timeout must be longer, the balancer's or the app's?

The app's keep-alive must outlast the balancer's idle timeout, or the balancer sends requests down connections the app has closed.

Why avoid sticky sessions?

They tie a user to one server: uneven load, and lost state when it restarts. Keep state in a database or token instead.

How do you test this?

On a real port, sending requests from two local addresses: one plays the balancer.

## Self-check rubric

| Area        | Meets the bar       | Above the bar                                                         |
|-------------|---------------------|-----------------------------------------------------------------------|
| Correctness | All 12 tests pass.  | You ran the flawed version and explained each failure.                |
| Trust       | Forward headers on. | Only the balancer trusted; you can say why Boot's default is risky.   |
| Links       | https links.        | Links built from the request, never from a Host header or a constant. |
| Timeouts    | A read timeout.     | Every hop's timeout, and which must be longer.                        |

# 3 · Go deeper: Review

## The pull request

A teammate "fixes the balancer issues in code": the office check reads the client from X-Forwarded-For, "because behind the balancer getRemoteAddr() is the balancer", and the upload's Location is built from the Host header the client used. Read both files and list every problem before opening the findings.

#### `review/SecurityConfig.java`

``` code
package com.mapwise.edge;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.authorization.AuthorizationDecision;
import org.springframework.security.authorization.AuthorizationManager;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.crypto.factory.PasswordEncoderFactories;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.provisioning.InMemoryUserDetailsManager;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.access.intercept.RequestAuthorizationContext;
import org.springframework.security.web.util.matcher.IpAddressMatcher;

@Configuration
class SecurityConfig {

    @Bean
    SecurityFilterChain api(HttpSecurity http, ProblemResponses problems, @Value("${mapwise.office-network}") String officeNetwork) throws Exception {
        IpAddressMatcher office = new IpAddressMatcher(officeNetwork);
        // Behind the load balancer getRemoteAddr() is the balancer, so take the client from X-Forwarded-For.
        AuthorizationManager<RequestAuthorizationContext> adminFromOffice = (auth, ctx) -> new AuthorizationDecision(
                auth.get().getAuthorities().stream().anyMatch(a -> a.getAuthority().equals("ROLE_ADMIN"))
                        && fromNetwork(office, clientIp(ctx.getRequest())));
        http.authorizeHttpRequests(a -> a
                        .requestMatchers(HttpMethod.GET, "/whoami").permitAll()
                        .requestMatchers(HttpMethod.POST, "/uploads").authenticated()
                        .requestMatchers(HttpMethod.GET, "/uploads/*").authenticated()
                        .requestMatchers(HttpMethod.GET, "/admin/uploads").access(adminFromOffice)
                        .requestMatchers("/error").permitAll()
                        .anyRequest().denyAll())
                .httpBasic(b -> b.authenticationEntryPoint(problems::unauthenticated))
                .exceptionHandling(x -> x.authenticationEntryPoint(problems::unauthenticated).accessDeniedHandler(problems::forbidden))
                // No session: any server behind the balancer can answer any request, so no sticky sessions are needed.
                .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .csrf(csrf -> csrf.disable());   // credentials in a header with every request, no cookie a browser sends by itself
        return http.build();
    }

    /** The first address in X-Forwarded-For is the original client; the rest are proxies. */
    static String clientIp(jakarta.servlet.http.HttpServletRequest req) {
        String forwardedFor = req.getHeader("X-Forwarded-For");
        return forwardedFor == null ? req.getRemoteAddr() : forwardedFor.split(",")[0].strip();
    }

    static boolean fromNetwork(IpAddressMatcher network, String address) {
        try {
            return network.matches(address);
        } catch (IllegalArgumentException notAnAddress) {
            return false;
        }
    }

    @Bean
    PasswordEncoder passwordEncoder() {
        return PasswordEncoderFactories.createDelegatingPasswordEncoder();
    }

    /** Demo users, password: the name plus "-demo-pass". */
    @Bean
    InMemoryUserDetailsManager users(PasswordEncoder encoder) {
        return new InMemoryUserDetailsManager(
                User.withUsername("asha").password(encoder.encode("asha-demo-pass")).roles("USER").build(),
                User.withUsername("vikram").password(encoder.encode("vikram-demo-pass")).roles("USER").build(),
                User.withUsername("ops").password(encoder.encode("ops-demo-pass")).roles("USER", "ADMIN").build());
    }
}
```

#### `review/UploadController.java`

``` code
package com.mapwise.edge;

import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RestController;

import java.io.IOException;
import java.util.Collection;

@RestController
class UploadController {

    private final Uploads uploads;

    UploadController(Uploads uploads) {
        this.uploads = uploads;
    }

    /** 201 with a Location for the new upload. */
    @PostMapping("/uploads")
    ResponseEntity<Uploads.Upload> upload(HttpServletRequest req, Authentication auth) throws IOException {
        Uploads.Upload saved = uploads.save(auth.getName(), req.getRemoteAddr(), req.getInputStream());
        // The link the client used: its Host header.
        return ResponseEntity.created(java.net.URI.create("http://" + req.getHeader("Host") + "/uploads/" + saved.id())).body(saved);
    }

    /** Another user's upload is a 404, the same as one that does not exist. */
    @GetMapping("/uploads/{id}")
    Uploads.Upload upload(@PathVariable long id, Authentication auth) {
        return uploads.find(auth.getName(), id).orElseThrow(() ->
                new ErrorResponseException(HttpStatus.NOT_FOUND, ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, "No such upload."), null));
    }

    /** Admins, from the office network only (see SecurityConfig). */
    @GetMapping("/admin/uploads")
    Collection<Uploads.Upload> all() {
        return uploads.all();
    }
}
```

## Findings

1The office check believes the client

"Behind the balancer getRemoteAddr() is the balancer": not with forward headers on, it is the client. And the first entry of X-Forwarded-For is whatever the client wrote: a client at home sends `203.0.113.9` and is in the office. Straight to the app it works the same way.

**Test evidence:** `theApiTrustsTheHeaderOnlyFromTheBalancerAndOnlyItsLastEntry` fails: the admin list answers `200` to a made-up header.

2Links from the Host header

`"http://" + Host` is the address the balancer used to reach the app, with http: `http://127.0.0.1:PORT/uploads/1` in the tests, `http://10.0.0.17:8080/...` in production. Clients that follow it go around the balancer, or fail. `ServletUriComponentsBuilder` uses the rewritten scheme, host and port.

**Test evidence:** `anUploadIsCountedAndItsLocationIsThePublicHttpsAddress` fails.

## Same tests, flawed version

From `docs/review-run.txt`: the flawed files copied over the real ones, then the full suite run.

| Test class                      | Fixed version | Flawed version |
|---------------------------------|---------------|----------------|
| `DefaultTrustedProxiesTrapTest` | 1 / 1         | 1 / 1          |
| `ProxySecurityTest`             | 4 / 4         | 4 / 4          |
| `TimeoutAndSessionTest`         | 2 / 2         | 2 / 2          |
| `ProxyContractTest`             | 3 / 3         | 2 / 3          |
| `SpoofedClientIpTrapTest`       | 2 / 2         | 1 / 2          |

Every honest request works on the flawed version. Its problems need a client who writes a header, and a client who follows a link: both happen on the first day in production.
