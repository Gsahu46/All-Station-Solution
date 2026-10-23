# Station 094 · Image previews without SSRF

Working Systems · 0–2 years · Core · Social · Types: Security

Spring Boot 4.1.1 · Java 25 · SSRF defences · Apache HttpClient 5 with a checking DNS resolver · timeouts and size limits · Spring Security 7. Needs JDK 25 (or 21, see Set up & code). No Docker, no database. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows). The tests use the loopback addresses 127.0.0.1 and 127.0.0.2, which Linux and Windows route by default; on macOS add 127.0.0.2 first (`sudo ifconfig lo0 alias 127.0.0.2`).

**Simulation:** The members, the news site and the "internal metadata service" are demo data: in the tests two small local servers stand for a public site and a cloud metadata service, and a stand-in for DNS points names at them. The secret is a made-up string.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 12 tests.

# 1 · Understand

## The problem in real life

1.  **A preview of the keys**

    Chaupal shows a preview when a member pastes a link. An attacker pasted http://169.254.169.254/latest/meta-data/iam/security-credentials/. The server fetched it, from inside the cloud, and the preview showed the server's access keys.

2.  **A check that looked once**

    The fix looked up the name, checked the address was public, and then fetched the URL. The fetch looked the name up again. The attacker's name answered a public address to the check and an internal one to the fetch.

3.  **The fix**

    The server looks every name up once, itself, refuses it if any address is internal, and connects to exactly the addresses it checked, also after redirects. It waits at most 3 seconds and reads at most 512 KB.

A server that fetches URLs for users is a door into your network. Check where each connection really goes, at the moment it goes.

## What are we building?

Link previews for members' draft posts, fetched only from the public internet, quickly and in small amounts.

## An everyday analogy

A receptionist who fetches documents for visitors, but only from outside the building, reads the address on the envelope themselves at the moment they leave, and gives up if it takes too long.

## How it works in 4 steps

1.  **Check the link**: http or https, a host, no user name in it.
2.  **Look the name up once**: if any address is loopback, private, link-local or similar, refuse.
3.  **Connect to those addresses**, with short timeouts; redirects go through steps 1 and 2 again.
4.  **Read a little**: HTML only, the first 512 KB, then take the title, description and image link.

Check yourself: the link is http://news.example/... and news.example has two addresses, one public and one 10.0.0.5. Fetch or not?

Refuse. The connection could go to either address, so one internal address is enough: `everyWayToNameAnInternalAddressIsRefused` (mixed.example).

## What this station is not

- **No image fetching.** The image is only linked; fetching it is challenge 2, with the same checks.
- **No cache.** Previews are kept in memory per member.
- **No HTML parser.** A few regular expressions read the title and Open Graph tags.

## Key terms

| Term                 | Simple meaning                                                                                      | Everyday example                                                          | In this project               |
|----------------------|-----------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------|-------------------------------|
| **Link preview**     | The title, text and picture shown when a link is pasted into a post.                                | The cover of a book seen through a shop window.                           | `POST /link-previews`         |
| **SSRF**             | Server-side request forgery: making a server fetch an address the attacker cannot reach themselves. | Asking the receptionist to fetch a file from the manager's locked office. | the metadata address          |
| **Metadata service** | An address inside cloud machines (169.254.169.254) that hands out the machine's keys.               | The key cabinet behind the counter.                                       | `169.254.169.254`             |
| **Private address**  | An address only reachable inside a network: 10.x, 192.168.x, 127.0.0.1...                           | A room number inside the building.                                        | `AddressPolicy`               |
| **DNS rebinding**    | A name that answers a safe address when checked and an internal one when used.                      | A visitor whose badge says "guest" at the door and "staff" inside.        | `rebind.example`              |
| **Timeout**          | The longest the server waits for a page.                                                            | Hanging up after three rings.                                             | 2 s to connect, 3 s to answer |

# 2 · Build: Spec

## Business problem

**Chaupal** (a fictional community app): a "preview this link" feature let an attacker read the cloud metadata service through our server.

## Acceptance criteria

Demo users: members meera and dev, and a guest; password `name-demo-pass`. Demo rules: 2 s to connect, 3 s to answer, 3 redirects, 512 KB.

1.  **Given** a public web page, **then** `201` with its title, description and an absolute image link.
2.  **Given** any address that is loopback, private, link-local, "this network", carrier-grade NAT, multicast or IPv6 unique-local, by IP, by name, among several addresses, or after a redirect, **then** `422`, without connecting.
3.  **Given** a name that changes its answer, **then** the address checked is the address used.
4.  **Given** another scheme, no host or a user name in the link, **then** `400`.
5.  **Given** a slow page, **then** `504` within about 3 s; a huge page, only its first 512 KB.
6.  **Given** another member's preview, **then** `404`; a guest, `403`; no sign-in, `401`.

## Requirements

- One lookup per connection, checked and used together.
- Limits on time, size, redirects and type.
- No fetch of the image by the server (until challenge 2 adds it with the same checks).

## Learning objectives

- Recognise SSRF and why cloud metadata makes it serious.
- Block address ranges, not host names.
- Defeat DNS rebinding by pinning the checked addresses.
- Put timeouts and size limits on every outgoing request.

# 2 · Build: API contract

## Endpoints

| Method | Path                  | Purpose                                                           |
|--------|-----------------------|-------------------------------------------------------------------|
| `POST` | `/link-previews`      | `{url}`: fetch the page safely and keep a preview for the member. |
| `GET`  | `/link-previews/{id}` | The member's own preview.                                         |

## Status codes

| Status    | When                                                                          |
|-----------|-------------------------------------------------------------------------------|
| 200 / 201 | The preview / created                                                         |
| 400       | Not a link; not http or https; no host; a user name in it                     |
| 401 / 403 | No sign-in / a guest                                                          |
| 404       | No such preview for this member                                               |
| 422       | A blocked address; no such host; not HTML; not 200; too many or bad redirects |
| 502 / 504 | The page could not be fetched / took more than 3 s                            |

## Captured examples

Captured with curl from the running app on 23 Oct 2026, in this order. The running app uses real DNS, and every address it could reach while capturing is private: these are refusals. Successful previews are shown by the tests, against the test sites. JSON bodies are indented for reading; `Date`, connection and standard security headers are left out.

### Case 1: the cloud metadata address

**Why:** 169.254.169.254 is link-local: `422`.

Request

``` code
POST /link-previews HTTP/1.1
Authorization: Basic bWVlcmE6bWVlcmEtZGVtby1wYXNz
Content-Type: application/json

{
  "url": "http://169.254.169.254/latest/meta-data/iam/security-credentials/"
}
```

Response

``` code
HTTP/1.1 422 
Content-Type: application/problem+json

{
  "detail": "This address cannot be previewed",
  "instance": "/link-previews",
  "status": 422,
  "title": "Unprocessable Content"
}
```

### Case 2: the app itself, on localhost

**Why:** loopback: `422`.

Request

``` code
POST /link-previews HTTP/1.1
Authorization: Basic bWVlcmE6bWVlcmEtZGVtby1wYXNz
Content-Type: application/json

{
  "url": "http://localhost:8080/actuator"
}
```

Response

``` code
HTTP/1.1 422 
Content-Type: application/problem+json

{
  "detail": "This address cannot be previewed",
  "instance": "/link-previews",
  "status": 422,
  "title": "Unprocessable Content"
}
```

### Case 3: \[::1\]

**Why:** IPv6 loopback: `422`.

Request

``` code
POST /link-previews HTTP/1.1
Authorization: Basic bWVlcmE6bWVlcmEtZGVtby1wYXNz
Content-Type: application/json

{
  "url": "http://[::1]:8080/"
}
```

Response

``` code
HTTP/1.1 422 
Content-Type: application/problem+json

{
  "detail": "This address cannot be previewed",
  "instance": "/link-previews",
  "status": 422,
  "title": "Unprocessable Content"
}
```

### Case 4: 10.0.0.5

**Why:** a private network: `422`.

Request

``` code
POST /link-previews HTTP/1.1
Authorization: Basic bWVlcmE6bWVlcmEtZGVtby1wYXNz
Content-Type: application/json

{
  "url": "http://10.0.0.5/admin"
}
```

Response

``` code
HTTP/1.1 422 
Content-Type: application/problem+json

{
  "detail": "This address cannot be previewed",
  "instance": "/link-previews",
  "status": 422,
  "title": "Unprocessable Content"
}
```

### Case 5: file:///etc/passwd

**Why:** only http and https: `400`.

Request

``` code
POST /link-previews HTTP/1.1
Authorization: Basic bWVlcmE6bWVlcmEtZGVtby1wYXNz
Content-Type: application/json

{
  "url": "file:///etc/passwd"
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Only http and https links to a host can be previewed",
  "instance": "/link-previews",
  "status": 400,
  "title": "Bad Request"
}
```

### Case 6: nosuch.invalid

**Why:** `.invalid` never resolves: `422`.

Request

``` code
POST /link-previews HTTP/1.1
Authorization: Basic bWVlcmE6bWVlcmEtZGVtby1wYXNz
Content-Type: application/json

{
  "url": "http://nosuch.invalid/"
}
```

Response

``` code
HTTP/1.1 422 
Content-Type: application/problem+json

{
  "detail": "No such host",
  "instance": "/link-previews",
  "status": 422,
  "title": "Unprocessable Content"
}
```

### Case 7: a guest

**Why:** `403`: previews are for members.

Request

``` code
POST /link-previews HTTP/1.1
Authorization: Basic Z3Vlc3Q6Z3Vlc3QtZGVtby1wYXNz
Content-Type: application/json

{
  "url": "http://169.254.169.254/"
}
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
  "instance": "/link-previews"
}
```

### Case 8: no sign-in

**Why:** `401`.

Request

``` code
POST /link-previews HTTP/1.1
Content-Type: application/json

{
  "url": "http://169.254.169.254/"
}
```

Response

``` code
HTTP/1.1 401 
WWW-Authenticate: Basic realm="chaupal"
Content-Type: application/problem+json
Content-Length: 116

{
  "title": "Sign-in required",
  "status": 401,
  "detail": "Send a valid username and password.",
  "instance": "/link-previews"
}
```

Timed by `docs/capture.sh`: The metadata address was refused after 100 ms (rounded down to 100 ms); the connect timeout is 2,000 ms. Refused at the lookup, before any connection could wait.

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                                                                 | What happens                                                    | Proved by                                       |
|------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------|-------------------------------------------------|
| A public page                                                                                        | Title, description, absolute image link; readable by its member | `aPublicPageGivesATitleDescriptionAndImageLink` |
| A redirect to a public page                                                                          | Followed; relative links resolve against the final page         | `aSafeRedirectIsFollowed`                       |
| An image, a 404, an unknown host, a redirect loop, not a link                                        | `422` or `400` with a plain reason                              | `whatCannotBePreviewedIsSaidPlainly`            |
| Loopback, IPv6, mapped IPv4, 0.0.0.0, metadata, private, CGNAT, ULA, a mixed name, a redirect inside | `422`                                                           | `everyWayToNameAnInternalAddressIsRefused`      |
| file:, gopher:, ftp:, no host, user info, javascript:; a redirect to file:                           | `400`; `422`                                                    | `onlyHttpAndHttpsToAHost`                       |
| Each address rule                                                                                    | Blocked or open, one by one                                     | `theAddressRulesOneByOne`                       |
| No sign-in, a guest, another member's preview                                                        | `401`, `403`, `404`                                             | `signInRulesAndAnotherMembersPreview`           |
| A page that answers after 10 s                                                                       | `504` after about 3 s                                           | `aSlowPageTimesOut`                             |
| A page that never ends                                                                               | The first 512 KB, in under 2 s                                  | `aHugePageIsReadOnlyAsFarAsAPreviewNeeds`       |

## The trap

Plausible but wrong

Fetching any URL the user sends, including internal addresses.

- **The old way.** `openStream()` on the internal address returns the secret.
- **Check, then fetch.** The test looks up `rebind.example` (a public address: "go ahead"), then the fetch looks it up again and gets the internal one: the secret again.
- **The API.** `metadata.internal` is refused. `rebind.example` is looked up once, checked, and fetched from that same public address: the news page, and exactly one lookup.

While building, each part was undone once: no address check turned 2 tests red; checking only the first address 1; no link-local 2; no carrier-grade NAT 2; no IPv6 unique-local 2; no scheme check 1; user info allowed 1; no size cap 1; no cancel after the cap 1; long timeouts 1; no type check 1; any member's preview 1.

``` code
package com.chaupal.previews;

import org.junit.jupiter.api.Test;

import java.io.InputStream;
import java.net.InetAddress;
import java.net.URI;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Written first. The old preview fetched any URL it was sent. An attacker sent the cloud metadata address and read the
 * instance's keys in the "preview". A later fix checked the name's address first, then fetched: a name that answers
 * a public address once and an internal one the next time (DNS rebinding) walked straight through.
 */
class FetchAnyUrlTrapTest extends ApiTest {

    @Test
    void theOldWayReadTheInternalSecret() throws Exception {
        try (InputStream in = URI.create(TestSites.url("127.0.0.1", "/latest/meta-data/iam/security-credentials/")).toURL().openStream()) {
            assertThat(new String(in.readAllBytes())).isEqualTo(TestSites.SECRET);
        }
    }

    @Test
    void checkingFirstAndFetchingLaterWasFooledByRebinding() throws Exception {
        AddressPolicy policy = new AddressPolicy(java.util.List.of("127.0.0.2"));
        InetAddress checked = TestSites.lookup("rebind.example")[0];
        assertThat(policy.isBlocked(checked)).isFalse();                    // "it is public, go ahead"
        InetAddress connectedTo = TestSites.lookup("rebind.example")[0];    // the fetch resolves the name again
        try (InputStream in = URI.create(TestSites.url(connectedTo.getHostAddress(), "/")).toURL().openStream()) {
            assertThat(new String(in.readAllBytes())).isEqualTo(TestSites.SECRET);
        }
    }

    @Test
    void theApiRefusesInternalAddressesAndIsNotFooledByRebinding() throws Exception {
        preview(TestSites.url("metadata.internal", "/latest/meta-data/iam/security-credentials/")).andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.detail").value("This address cannot be previewed"));
        TestSites.rebindLookups.set(0);
        preview(TestSites.url("rebind.example", "/article")).andExpect(status().isCreated())
                .andExpect(jsonPath("$.title").value("Monsoon reaches Kerala early"));   // checked and fetched from the same, public address
        assertThat(TestSites.rebindLookups.get()).isOne();                                // one lookup: no second answer to trust
    }
}
```

# 2 · Build: Set up & code

## Set up and run

| You need   | Version                                                        | Check with                          |
|------------|----------------------------------------------------------------|-------------------------------------|
| JDK        | 25 (recommended). JDK 21 also works, see below                 | `java -version`                     |
| Maven      | Not needed: the project ships the Maven wrapper                |                                     |
| macOS only | The address 127.0.0.2 on the loopback interface, for the tests | `sudo ifconfig lo0 alias 127.0.0.2` |

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

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Ask for a preview of the app itself, as Meera:

``` code
curl -u meera:meera-demo-pass -H 'Content-Type: application/json' -d '{"url": "http://localhost:8080/actuator"}' http://localhost:8080/link-previews
```

It answers `422` "This address cannot be previewed", as in case 2. With internet access, a public news page gives `201` and its title.

## Troubleshooting

| You see                                           | Cause                                                                | Fix                                                                    |
|---------------------------------------------------|----------------------------------------------------------------------|------------------------------------------------------------------------|
| Tests fail to bind 127.0.0.2 (macOS)              | macOS routes only 127.0.0.1 by default.                              | `sudo ifconfig lo0 alias 127.0.0.2`                                    |
| A huge page times out instead of stopping         | The client reads the rest of the body to reuse the connection.       | Cancel the request after reading what you need, as `SafeFetcher` does. |
| Every preview is refused behind a corporate proxy | The fetcher connects directly; a proxy changes where connections go. | Then the proxy must enforce the same rules (challenge 3).              |

## Project layout

``` tree
stations/094-image-previews-without-ssrf/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/chaupal/previews/
│   ├── SecurityConfig.java   ├── PreviewController.java   ├── Previews.java
│   ├── SafeFetcher.java   ├── AddressPolicy.java   ├── NameLookup.java
│   └── ProblemResponses.java   └── PreviewsApplication.java
├── src/main/resources/application.yaml
├── src/test/java/com/chaupal/previews/   (see Tests; TestSites.java runs the two test servers)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels.

#### `src/main/java/com/chaupal/previews/SecurityConfig.java`

Does  
Who may preview.

Why  
HTTP Basic; members create and read; guests nothing.

Without it  
Anyone using the server as a fetcher.

#### `src/main/java/com/chaupal/previews/PreviewController.java`

Does  
The endpoints.

Why  
Parses the link, hands it to `Previews`.

Without it  
Links that are not links reaching the fetcher.

#### `src/main/java/com/chaupal/previews/Previews.java`

Does  
Making and keeping previews.

Why  
Fetches the page safely, reads the title and Open Graph tags, keeps the preview for its member.

Without it  
One member reading another's drafts.

The image link is returned, never fetched by the server.

#### `src/main/java/com/chaupal/previews/SafeFetcher.java`

Does  
Fetching safely.

Why  
Apache HttpClient with our `DnsResolver`: each name resolved once and refused if any address is blocked, then connected to exactly those addresses. Timeouts, 3 redirects, HTML only, the first 512 KB.

Without it  
SSRF, DNS rebinding, redirects inside, and pages that never end.

- The resolver is the only place names become addresses, so the check and the connection cannot disagree.
- When more than 512 KB is coming, the request is cancelled: otherwise the client reads the rest to reuse the connection, and an endless page timed out. Found while building.
- A redirect to `file:` surfaces as a protocol error; it is answered `422`.

#### `src/main/java/com/chaupal/previews/AddressPolicy.java`

Does  
Which addresses are internal.

Why  
Loopback, private, link-local, any-local, 0/8, 100.64/10, multicast, fc00::/7. A list of exceptions exists for tests only.

Without it  
Missing a range an attacker can use.

No check for IPv6 addresses wrapping IPv4 ones: Java turns `::ffff:127.0.0.1` into 127.0.0.1 itself. A first version had the check; removing it changed no test. Found while building.

#### `src/main/java/com/chaupal/previews/NameLookup.java`

DNS as one method, so tests can point names at local servers and make one change its answer.

#### `src/main/java/com/chaupal/previews/ProblemResponses.java`

`401` and `403` in the same problem shape as other errors.

#### `src/main/resources/application.yaml`

The exception list, empty.

#### `src/main/java/com/chaupal/previews/PreviewsApplication.java`

Entry point, and real DNS.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                                       | Test class                                       | Result |
|---------------|-------------------------------------------------------------------|--------------------------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found                          | `PreviewContractTest` (3), `FetchLimitsTest` (2) | pass   |
| Every station | Reproduce the failure before the fix                              | `FetchAnyUrlTrapTest` (3)                        | pass   |
| Security      | 401, 403, one user accessing another user's data, malicious input | `SsrfSecurityTest` (4)                           | pass   |

The tests need a "public" site and an "internal" one on the same machine: `TestSites` runs a news site on 127.0.0.2 and a metadata service on 127.0.0.1, on the same port, and a stand-in for DNS. Only 127.0.0.2 is on the test exception list; 127.0.0.1 stays blocked, like every private address.

## Run output

JDK 25.0.1, Spring Boot 4.1.1, Apache HttpClient 5.6.4. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.chaupal.previews.PreviewContractTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.chaupal.previews.FetchLimitsTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.chaupal.previews.SsrfSecurityTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.chaupal.previews.FetchAnyUrlTrapTest
[INFO] Tests run: 12, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/chaupal/previews/FetchAnyUrlTrapTest.java`

Written first: the old fetch, check-then-fetch with rebinding, and the API.

#### `src/test/java/com/chaupal/previews/SsrfSecurityTest.java`

Every way to name an internal address, other schemes, each rule, sign-in.

#### `src/test/java/com/chaupal/previews/PreviewContractTest.java`

Previews of the test news site; what cannot be previewed.

#### `src/test/java/com/chaupal/previews/FetchLimitsTest.java`

A slow page and an endless one.

#### `src/test/java/com/chaupal/previews/TestSites.java`

The two test servers and the test DNS.

#### `src/test/java/com/chaupal/previews/ApiTest.java`

Shared setup: the test DNS as a bean, the exception for 127.0.0.2, request helpers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/chaupal/previews/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=AllowedDomainsChallengeTest`.
3.  Change the code until it passes, then run `./mvnw test` to check the other 12 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 15 tests pass (12 station tests and 3 challenge tests).

Challenge 1 · Beginner-friendly · about 20 minutes

## Only some sites

`chaupal.previews.allowed-domains`, when set, limits previews to those sites and their subdomains: `fakenews.example` is not `news.example`, and an IP address is no site. The address rules still apply.

**Done when:** the test in `AllowedDomainsChallengeTest` passes.

Hints

- Compare the lower-cased host with each domain, or with `"." + domain` at its end.
- An empty list means no domain limit.

#### `challenge/AllowedDomainsChallengeTest.java`

``` code
package com.chaupal.previews;

import org.junit.jupiter.api.Test;
import org.springframework.test.context.TestPropertySource;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: chaupal.previews.allowed-domains, when set, limits previews to those sites and their subdomains. A name
 * that merely ends with the same letters is another site. The address rules still apply to allowed sites.
 */
@TestPropertySource(properties = "chaupal.previews.allowed-domains=news.example,rebind.example")
class AllowedDomainsChallengeTest extends ApiTest {

    @Test
    void onlyListedSitesCanBePreviewed() throws Exception {
        preview(TestSites.url("news.example", "/article")).andExpect(status().isCreated());
        preview(TestSites.url("mixed.example", "/article")).andExpect(status().isUnprocessableContent()).andExpect(jsonPath("$.detail").value("This site cannot be previewed"));
        preview(TestSites.url("fakenews.example", "/article")).andExpect(status().isUnprocessableContent()).andExpect(jsonPath("$.detail").value("This site cannot be previewed"));
        preview(TestSites.url("127.0.0.2", "/article")).andExpect(status().isUnprocessableContent()).andExpect(jsonPath("$.detail").value("This site cannot be previewed"));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 35 minutes

## Images through the server

`GET /link-previews/{id}/image` serves the preview's image, fetched by the server with the same checks as the page: only `image/*`, at most 1 MB. An `og:image` pointing inside is refused.

**Done when:** both tests in `ImageProxyChallengeTest` pass.

Hints

- Make the fetcher take the accepted type and the size limit.
- An image link is attacker-controlled exactly like the page link.

#### `challenge/ImageProxyChallengeTest.java`

``` code
package com.chaupal.previews;

import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.json.JsonMapper;

import java.net.InetAddress;
import java.net.InetSocketAddress;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: GET /link-previews/{id}/image serves the preview's image through the server, so members' apps never
 * contact the site. The image is fetched with the same checks as the page: an og:image pointing at an internal
 * address is refused, and only images (image/*) of at most 1 MB are passed on.
 */
class ImageProxyChallengeTest extends ApiTest {

    HttpServer site;

    @BeforeEach
    void aSiteWithImages() throws Exception {
        site = HttpServer.create(new InetSocketAddress(InetAddress.getByName("127.0.0.2"), 0), 0);
        int port = site.getAddress().getPort();
        site.createContext("/good", x -> page(x, "/cover.png"));
        site.createContext("/evil", x -> page(x, "http://127.0.0.1:" + TestSites.PORT + "/latest/meta-data/"));
        site.createContext("/notimage", x -> page(x, "/cover.html"));
        site.createContext("/cover.png", x -> {
            byte[] png = {(byte) 0x89, 'P', 'N', 'G', 0x0D, 0x0A, 0x1A, 0x0A};
            x.getResponseHeaders().set("Content-Type", "image/png");
            x.sendResponseHeaders(200, png.length);
            x.getResponseBody().write(png);
            x.close();
        });
        site.createContext("/cover.html", x -> {
            x.getResponseHeaders().set("Content-Type", "text/html");
            x.sendResponseHeaders(200, 2);
            x.getResponseBody().write("hi".getBytes());
            x.close();
        });
        site.start();
        base = "http://127.0.0.2:" + port;
    }

    String base;

    static void page(com.sun.net.httpserver.HttpExchange x, String image) throws java.io.IOException {
        byte[] b = ("<title>t</title><meta property=\"og:image\" content=\"" + image + "\">").getBytes();
        x.getResponseHeaders().set("Content-Type", "text/html");
        x.sendResponseHeaders(200, b.length);
        x.getResponseBody().write(b);
        x.close();
    }

    @AfterEach
    void stop() {
        site.stop(0);
    }

    String previewId(String path) throws Exception {
        return JsonMapper.builder().build().readTree(preview(base + path).andReturn().getResponse().getContentAsString()).get("id").asString();
    }

    @Test
    void theImageComesThroughTheServer() throws Exception {
        read("meera", previewId("/good") + "/image").andExpect(status().isOk()).andExpect(content().contentType("image/png"));
    }

    @Test
    void anImagePointingInsideIsRefusedAndSoIsSomethingElse() throws Exception {
        read("meera", previewId("/evil") + "/image").andExpect(status().isUnprocessableContent()).andExpect(jsonPath("$.detail").value("This address cannot be previewed"));
        read("meera", previewId("/notimage") + "/image").andExpect(status().isUnprocessableContent());
        read("dev", previewId("/good") + "/image").andExpect(status().isNotFound());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## An egress proxy

Instead of checking addresses in the app, send every outgoing fetch through a separate egress proxy that can only reach the internet (no route to private networks, metadata blocked by the network itself). What does the app still check, what moves to the network, and what do you gain when a second team also needs to fetch URLs? Add the cloud provider's own protection (for example, metadata that requires a session token).

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test with a public and an internal test server.
2.  Write the address policy and test each range.
3.  Put the policy in the HTTP client's DNS resolver, so every connection, redirects included, is checked where it is made.
4.  Add timeouts, the size cap, the type check and the member rules.

## Design alternatives and trade-offs

| Approach                                                | What it costs                                                 | Verdict                             |
|---------------------------------------------------------|---------------------------------------------------------------|-------------------------------------|
| Check in the resolver, connect to the checked addresses | A client that lets you plug in DNS (Apache HttpClient does).  | Chosen                              |
| Fetch anything                                          | The metadata service, the admin panel, everything inside.     | The trap                            |
| Check the address, then fetch by name                   | DNS rebinding; redirects unchecked.                           | The first fix                       |
| A block-list of host names                              | Endless ways to write an address: IPv6, decimal, other names. | Review finding                      |
| An egress proxy with network rules                      | Infrastructure; protects every service at once.               | Best, with app checks (challenge 3) |

## Database design

This station has no database: previews are kept in memory per member (a `shortcut:` comment says so). A real service would cache previews by URL with an expiry, and never cache a refusal as a preview.

# 3 · Go deeper: Production

Defence in depth  
Block metadata at the cloud level too (for example, metadata that requires a session token) and give the server no network route to private ranges.

More ranges  
NAT64 prefixes (64:ff9b::/96) and your own public addresses can also reach inside: add them where they exist.

Abuse  
Previews make your server fetch for others: rate-limit per member, and watch for scanning patterns (many hosts, many ports).

Logs  
Log refusals with the member and the address: they are often the first sign of an attack.

# 3 · Go deeper: Interview

## Interview takeaways

What is SSRF?

Server-side request forgery: getting a server to make requests the attacker chooses, to places only the server can reach, such as internal services and cloud metadata.

Why is a host-name block-list not enough?

An address can be written many ways (IPv6, decimal, other names pointing at it), and redirects lead elsewhere. Check the resolved addresses, at connect time.

What is DNS rebinding?

A name that resolves to a safe address when checked and an internal one when used. Resolve once and connect to the checked address.

Which addresses do you block?

Loopback, private ranges, link-local (with 169.254.169.254), any-local, 0/8, carrier-grade NAT, multicast, IPv6 unique-local, and anything else that routes inside.

What limits does a server-side fetch need?

Timeouts for connect and read, a cap on size, few redirects, an expected content type, and a rate limit per user.

## Self-check rubric

| Area        | Meets the bar                  | Above the bar                                                                              |
|-------------|--------------------------------|--------------------------------------------------------------------------------------------|
| Correctness | All 12 tests pass.             | You ran the flawed version and explained each failure.                                     |
| Addresses   | Loopback and metadata blocked. | Every internal range, every spelling, every address of a name.                             |
| Rebinding   | Checked before fetching.       | Checked where the connection is made, redirects included.                                  |
| Limits      | A timeout.                     | Connect and read timeouts, a size cap that really stops reading, type and redirect limits. |

# 3 · Go deeper: Review

## The pull request

A teammate simplifies the fetcher: the URL's host is checked against a short list of internal hosts before fetching, and the resolver stops checking, "since the URL was already checked". Read the file and list every problem before opening the findings.

#### `review/SafeFetcher.java`

``` code
package com.chaupal.previews;

import org.apache.hc.client5.http.DnsResolver;
import org.apache.hc.client5.http.classic.methods.HttpGet;
import org.apache.hc.client5.http.config.ConnectionConfig;
import org.apache.hc.client5.http.config.RequestConfig;
import org.apache.hc.client5.http.impl.classic.CloseableHttpClient;
import org.apache.hc.client5.http.impl.classic.HttpClients;
import org.apache.hc.client5.http.impl.io.PoolingHttpClientConnectionManagerBuilder;
import org.apache.hc.client5.http.protocol.HttpClientContext;
import org.apache.hc.core5.http.ContentType;
import org.apache.hc.core5.util.Timeout;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.stereotype.Component;
import org.springframework.web.ErrorResponseException;

import java.io.IOException;
import java.io.InputStream;
import java.net.InetAddress;
import java.net.SocketTimeoutException;
import java.net.URI;
import java.net.UnknownHostException;
import java.nio.charset.StandardCharsets;
import java.util.Locale;

/**
 * Fetches a page for a preview, safely. Every name is resolved once, by our resolver, which refuses it if any of its
 * addresses is blocked; the connection then goes to exactly those addresses. So a check cannot be fooled by a name
 * that answers differently the second time (DNS rebinding), and redirects go through the same check.
 */
@Component
class SafeFetcher {

    static final int MAX_BYTES = 512 * 1024;
    static final int MAX_REDIRECTS = 3;

    record Page(URI finalUri, String html) {
    }

    static final class Blocked extends UnknownHostException {
        Blocked(String host) {
            super(host + " resolves to an address that is not allowed");
        }
    }

    /** The internal hosts an attacker would try. */
    static final java.util.Set<String> BLOCKED_HOSTS = java.util.Set.of("localhost", "127.0.0.1", "169.254.169.254", "metadata.google.internal");

    private final CloseableHttpClient http;

    SafeFetcher(AddressPolicy policy, NameLookup lookup) {
        DnsResolver checked = new DnsResolver() {
            @Override
            public InetAddress[] resolve(String host) throws UnknownHostException {
                return lookup.lookup(host);   // the URL was checked in fetch(): no need to check again here
            }

            @Override
            public String resolveCanonicalHostname(String host) {
                return host;
            }
        };
        this.http = HttpClients.custom()
                .setConnectionManager(PoolingHttpClientConnectionManagerBuilder.create().setDnsResolver(checked)
                        .setDefaultConnectionConfig(ConnectionConfig.custom().setConnectTimeout(Timeout.ofSeconds(2)).setSocketTimeout(Timeout.ofSeconds(3)).build())
                        .build())
                .setDefaultRequestConfig(RequestConfig.custom().setResponseTimeout(Timeout.ofSeconds(3)).setMaxRedirects(MAX_REDIRECTS).build())
                .disableCookieManagement()
                .setUserAgent("ChaupalPreview/1.0")
                .build();
    }

    Page fetch(URI uri) {
        String scheme = uri.getScheme() == null ? "" : uri.getScheme().toLowerCase(Locale.ROOT);
        if (!(scheme.equals("http") || scheme.equals("https")) || uri.getHost() == null || uri.getRawUserInfo() != null) {
            throw problem(HttpStatus.BAD_REQUEST, "Only http and https links to a host can be previewed");
        }
        if (BLOCKED_HOSTS.contains(uri.getHost().toLowerCase(Locale.ROOT))) {
            throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "This address cannot be previewed");
        }
        HttpGet get = new HttpGet(uri);
        get.addHeader("Accept", "text/html");
        HttpClientContext context = HttpClientContext.create();
        try {
            return http.execute(get, context, response -> {
                if (response.getCode() != 200) {
                    throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "The page answered " + response.getCode());
                }
                ContentType type = ContentType.parseLenient(response.getEntity().getContentType());
                if (type == null || !type.getMimeType().equalsIgnoreCase("text/html")) {
                    throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "The link is not a web page");
                }
                try (InputStream in = response.getEntity().getContent()) {
                    byte[] head = in.readNBytes(MAX_BYTES);   // a preview needs the head of a page, never the whole of a huge one
                    if (in.read() != -1) {
                        get.cancel();   // more is coming: drop the connection rather than read (or wait for) the rest
                    }
                    var redirects = context.getRedirectLocations().getAll();
                    URI finalUri = redirects.isEmpty() ? uri : redirects.getLast();   // relative links resolve against the page we ended on
                    return new Page(finalUri, new String(head, type.getCharset() == null ? StandardCharsets.UTF_8 : type.getCharset()));
                }
            });
        } catch (ErrorResponseException e) {
            throw e;
        } catch (Blocked e) {
            throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "This address cannot be previewed");
        } catch (UnknownHostException e) {
            throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "No such host");
        } catch (SocketTimeoutException e) {   // ConnectTimeoutException is one too
            throw problem(HttpStatus.GATEWAY_TIMEOUT, "The page took too long to answer");
        } catch (IOException e) {
            if (e.getCause() instanceof org.apache.hc.client5.http.RedirectException) {
                throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "Too many redirects");
            }
            if (e.getCause() instanceof org.apache.hc.core5.http.ProtocolException) {
                throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "The page redirects to a link that cannot be previewed");   // file:, no host...
            }
            throw problem(HttpStatus.BAD_GATEWAY, "The page could not be fetched");
        }
    }

    static ErrorResponseException problem(HttpStatus status, String detail) {
        return new ErrorResponseException(status, ProblemDetail.forStatusAndDetail(status, detail), null);
    }
}
```

## Findings

1A block-list of host names

"The internal hosts an attacker would try": localhost, 127.0.0.1, 169.254.169.254. But \[::1\], 0.0.0.0, 10.0.0.5, any name that points inside, and a public page that redirects to 127.0.0.1 all pass. An attacker only needs one spelling the list does not have.

**Test evidence:** `everyWayToNameAnInternalAddressIsRefused` fails.

2No check where the connection is made

"The URL was checked in fetch()": the resolver now returns whatever DNS says, so a name pointing inside (metadata.internal) is fetched, and redirects are never checked at all.

**Test evidence:** `theApiRefusesInternalAddressesAndIsNotFooledByRebinding` fails.

## Same tests, flawed version

From `docs/review-run.txt`: the flawed file copied over the real one, then the full suite run.

| Test class            | Fixed version | Flawed version |
|-----------------------|---------------|----------------|
| `FetchLimitsTest`     | 2 / 2         | 2 / 2          |
| `PreviewContractTest` | 3 / 3         | 3 / 3          |
| `FetchAnyUrlTrapTest` | 3 / 3         | 2 / 3          |
| `SsrfSecurityTest`    | 4 / 4         | 3 / 4          |

The three addresses on the list are refused, and the obvious attack in a manual test fails. Only two tests fail, but each holds many attacks: one bypass is all it takes.
