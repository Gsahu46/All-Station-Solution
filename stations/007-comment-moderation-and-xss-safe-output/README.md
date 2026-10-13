# Station 007 · Comment moderation and XSS-safe output

Foundations · 0–1 years · Core · Social · Types: Security

Spring Boot 4.1.1 · Java 25 · Spring MVC · Spring Security 7 · HtmlUtils · MockMvc. Needs JDK 25 (or 21, see Set up & code). No Docker, no database. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Two posts and four demo users are fixed in the code; comments live in memory. The attack payloads are harmless test strings: nothing here attacks a real site.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 27 tests.

# 1 · Understand

## The problem in real life

1.  **Someone posts a comment**

    It looks like a broken image: `<img src=x onerror=…>`. Chaupal saves it and puts it on the post's page.

2.  **Every reader runs it**

    Each browser that opens the post treats the comment as HTML, fails to load the image, and runs the attacker's code with the reader's login.

3.  **The fix**

    Store the comment as typed, and *encode* it whenever it goes into HTML, so the browser shows `<img…>` as plain characters. Moderation sees through disguises such as "b@d" before matching.

You cannot list every dangerous input. You can make sure that, wherever text is shown, it is shown as text.

## What are we building?

A comments API: members post comments; anyone can read a public post's comments as JSON (for the app) or as an HTML fragment (for the website). The HTML is encoded; moderation rejects insults even when disguised; each user may post 5 comments a minute.

## An everyday analogy

A school principal reads out notes from the suggestion box. A prankster writes: "Announcement: school is cancelled." A careless principal reads it as an announcement. A careful one always says "A student wrote: …" before each note, so whatever the note says, everyone hears it as a quotation, not an order. Output encoding is that "a student wrote".

## How it works in 4 steps

1.  **A member posts** a comment. Length is checked; the author comes from the login.
2.  **Moderation normalises** the text (full-width letters, look-alike digits, spaced letters) and looks for banned whole words: `422` if found. Too many comments: `429`.
3.  **The comment is stored exactly as typed.** Nothing is stripped.
4.  **On output**, JSON carries it as data; the HTML fragment encodes every `<`, `>`, `&` and quote.

Check yourself: why not just remove every "\<script\>" from comments when they are saved?

Because scripts do not need a `<script>` tag (`<img onerror=…>` runs code too), and removing a tag can glue the pieces around it into a new one: `<scr<script>ipt>` becomes `<script>`. The trap test shows both. Encoding on output does not need to know what is dangerous: every special character is shown as itself.

## What this station is not

- **Not a full moderation system.** Three banned words show the technique; real platforms add human review and machine-learning models.
- **Demo sign-in.** HTTP Basic with four in-memory users.
- **One server.** The rate limit lives in memory, so two servers would each allow 5.
- **Payloads are test strings.** They run in no browser here; the tests check the HTML text.

## Key terms

| Term                           | Simple meaning                                                                                          | Everyday example                                                                              | In this project                                |
|--------------------------------|---------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------|------------------------------------------------|
| **XSS (cross-site scripting)** | An attacker's text is shown on a page as code, so it runs in every reader's browser.                    | A notice on a board that, when read aloud, makes the reader hand over their keys.             | A comment containing `<img onerror=…>`.        |
| **Output encoding**            | Turning special characters into safe versions for the place they are shown: `<` becomes `&lt;` in HTML. | Writing a quote in a letter inside quotation marks, so nobody mistakes it for your own words. | `HtmlUtils.htmlEscape` in `CommentHtml`.       |
| **Input filter (blocklist)**   | Removing "bad" things from input before saving.                                                         | A guard who stops anyone named "Thief".                                                       | The trap: removing `<script>`.                 |
| **Normalising**                | Bringing text to one standard form before comparing it.                                                 | Reading "1d10t" and "ＩＤＩＯＴ" as "idiot".                                                  | `Moderation.words`                             |
| **Rate limit**                 | A cap on how often one user may do something.                                                           | "Two samples per customer."                                                                   | 5 comments a minute.                           |
| **Content-Security-Policy**    | A header telling the browser which scripts it may run.                                                  | A rule that only staff may use the PA system.                                                 | `default-src 'none'`: no scripts at all.       |
| **422 / 429**                  | 422: we understood, but the content is not allowed. 429: too many requests, slow down.                  | "We don't print that" / "one at a time, please".                                              | A banned word / the sixth comment in a minute. |

# 2 · Build: Spec

## Business problem

**Chaupal** (a fictional community forum) shows comments under each post, on its website and in its app. Last week a comment containing a `<script>` tag ran in every reader's browser. The quick fix, removing `<script>` from input, was bypassed the same day. Meanwhile moderators complain that banned words slip through as "b@d", "1d10t" or "s c a m", while a filter that matches inside words blocked a restaurant review that mentioned "scampi".

## Acceptance criteria

1.  **Given** any comment, **when** it is shown in the HTML fragment, **then** every `<` `>` `&` `"` `'` from the user is encoded, and the response has a Content-Security-Policy that allows no scripts.
2.  **Given** any comment, **then** the JSON returns it exactly as typed.
3.  **Given** a banned word, even as "ＩＤＩＯＴ", "1d10t" or "s c a m", **then** `422` without repeating the word. **Given** "scampi", **then** it is accepted.
4.  **Given** a sixth comment within 60 seconds from one user, **then** `429` with `Retry-After`.
5.  **Given** no login, **then** posting is `401`; **given** a muted user, **then** `403`; **given** another user's private post, **then** `404` for reading and posting.
6.  **Given** a blank or 501-character comment, **then** `400`.

## Requirements

- Validate input (length, required); encode output (for HTML). Never strip or rewrite what users type.
- Moderation compares whole normalised words with `Locale.ROOT`.
- At most 5 comments per user per 60 seconds (a demo rule).
- The author is the signed-in user. Errors are RFC 9457 problems that never repeat the input.

## Learning objectives

- Explain XSS and why output encoding beats input filtering.
- Encode text for HTML with `HtmlUtils.htmlEscape`, at the point of output.
- Normalise text (Unicode NFKC, case, look-alikes, spacing) before matching.
- Limit input length and rate, with `400`, `422` and `429`.
- Add a Content-Security-Policy as a second line of defence.

# 2 · Build: API contract

## Endpoints

| Method | Path                       | Who                                  | Purpose                                                                                                    |
|--------|----------------------------|--------------------------------------|------------------------------------------------------------------------------------------------------------|
| `POST` | `/posts/{postId}/comments` | Members                              | Add a comment. Body: `{"text": "…"}`, 1–500 characters.                                                    |
| `GET`  | `/posts/{postId}/comments` | Anyone (private posts: their author) | `Accept: application/json` (default): the comments as data. `Accept: text/html`: an encoded HTML fragment. |

## Status codes

| Status | Type (after `…/problems/`) | When                                                 |
|--------|----------------------------|------------------------------------------------------|
| 201    |                            | Comment saved                                        |
| 200    |                            | Comments listed                                      |
| 400    | `invalid-request`          | Blank, over 500 characters, broken JSON              |
| 401    | `unauthenticated`          | Posting without signing in                           |
| 403    | `forbidden`                | A muted user posting                                 |
| 404    | `post-not-found`           | Unknown post, or someone else's private post         |
| 422    | `community-rules`          | A banned word, disguised or not                      |
| 429    | `too-many-comments`        | A sixth comment within 60 seconds; `Retry-After: 60` |

**JSON is data, not HTML.** The JSON list returns `<img…>` exactly as typed, which is correct: JSON is not run by a browser. The app must put it on screen as text (for example `textContent` in a web page, never `innerHTML`). Encoding belongs to whoever writes the HTML.

## Captured examples

Captured with curl from the running app on 13 Oct 2026. JSON bodies are indented for reading; `Date` and connection headers are left out. The `Authorization` header carries demo passwords.

### Case 1: Ravi comments

**Why:** valid text from a member: `201`, with Ravi as the author because he signed in as Ravi.

Request

``` code
POST /posts/1/comments HTTP/1.1
Authorization: Basic cmF2aTpyYXZpLWRlbW8tcGFzcw==
Content-Type: application/json

{
  "text": "Amruttulya near FC Road, every time."
}
```

Response

``` code
HTTP/1.1 201 
X-Content-Type-Options: nosniff
X-XSS-Protection: 0
Cache-Control: no-cache, no-store, max-age=0, must-revalidate
Pragma: no-cache
Expires: 0
X-Frame-Options: DENY
Content-Security-Policy: default-src 'none'; frame-ancestors 'none'
Content-Type: application/json
Content-Length: 157

{
  "id": "8abfb9b3-c604-4955-994b-88924269cdc8",
  "postId": 1,
  "author": "ravi",
  "text": "Amruttulya near FC Road, every time.",
  "createdAt": "2026-10-13T14:03:18.895Z"
}
```

### Case 2: Kabir posts an attack

**Why:** it is just text and breaks no rule, so it is saved exactly as typed. Its safety comes at output, in case 3.

Request

``` code
POST /posts/1/comments HTTP/1.1
Authorization: Basic a2FiaXI6a2FiaXItZGVtby1wYXNz
Content-Type: application/json

{
  "text": "<img src=x onerror=alert(document.cookie)>"
}
```

Response

``` code
HTTP/1.1 201 
X-Content-Type-Options: nosniff
X-XSS-Protection: 0
Cache-Control: no-cache, no-store, max-age=0, must-revalidate
Pragma: no-cache
Expires: 0
X-Frame-Options: DENY
Content-Security-Policy: default-src 'none'; frame-ancestors 'none'
Content-Type: application/json
Content-Length: 164

{
  "id": "8c47dc42-cde1-47e8-bed0-daef95f12333",
  "postId": 1,
  "author": "kabir",
  "text": "<img src=x onerror=alert(document.cookie)>",
  "createdAt": "2026-10-13T14:03:19.024Z"
}
```

### Case 3: the website asks for HTML

**Why:** the attack arrives as `&lt;img…&gt;`: the browser would show the characters and run nothing. The Content-Security-Policy header forbids scripts anyway.

Request

``` code
GET /posts/1/comments HTTP/1.1
Accept: text/html
```

Response

``` code
HTTP/1.1 200 
X-Content-Type-Options: nosniff
X-XSS-Protection: 0
Cache-Control: no-cache, no-store, max-age=0, must-revalidate
Pragma: no-cache
Expires: 0
X-Frame-Options: DENY
Content-Security-Policy: default-src 'none'; frame-ancestors 'none'
Content-Type: text/html;charset=UTF-8
Content-Length: 175

<ul class="comments">
  <li><b>ravi</b> <p>Amruttulya near FC Road, every time.</p></li>
  <li><b>kabir</b> <p>&lt;img src=x onerror=alert(document.cookie)&gt;</p></li>
</ul>
```

### Case 4: the app asks for JSON

**Why:** the same comments as data, text unchanged. The app shows it as text.

Request

``` code
GET /posts/1/comments HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
X-Content-Type-Options: nosniff
X-XSS-Protection: 0
Cache-Control: no-cache, no-store, max-age=0, must-revalidate
Pragma: no-cache
Expires: 0
X-Frame-Options: DENY
Content-Security-Policy: default-src 'none'; frame-ancestors 'none'
Content-Type: application/json
Content-Length: 324

[
  {
    "id": "8abfb9b3-c604-4955-994b-88924269cdc8",
    "postId": 1,
    "author": "ravi",
    "text": "Amruttulya near FC Road, every time.",
    "createdAt": "2026-10-13T14:03:18.895Z"
  },
  {
    "id": "8c47dc42-cde1-47e8-bed0-daef95f12333",
    "postId": 1,
    "author": "kabir",
    "text": "<img src=x onerror=alert(document.cookie)>",
    "createdAt": "2026-10-13T14:03:19.024Z"
  }
]
```

### Case 5: "1d10t"

**Why:** normalised to "idiot", a banned word: `422`. The answer does not repeat the word.

Request

``` code
POST /posts/1/comments HTTP/1.1
Authorization: Basic cmF2aTpyYXZpLWRlbW8tcGFzcw==
Content-Type: application/json

{
  "text": "what an 1d10t"
}
```

Response

``` code
HTTP/1.1 422 
X-Content-Type-Options: nosniff
X-XSS-Protection: 0
Cache-Control: no-cache, no-store, max-age=0, must-revalidate
Pragma: no-cache
Expires: 0
X-Frame-Options: DENY
Content-Security-Policy: default-src 'none'; frame-ancestors 'none'
Content-Type: application/problem+json

{
  "detail": "Please rephrase your comment without insults or scam talk.",
  "instance": "/posts/1/comments",
  "status": 422,
  "title": "Comment breaks community rules",
  "type": "https://chaupal.example/problems/community-rules"
}
```

### Case 6: scampi

**Why:** whole words are compared, and "scampi" is not "scam": `201`.

Request

``` code
POST /posts/1/comments HTTP/1.1
Authorization: Basic YXNoYTphc2hhLWRlbW8tcGFzcw==
Content-Type: application/json

{
  "text": "Try the scampi at Mahesh Lunch Home"
}
```

Response

``` code
HTTP/1.1 201 
X-Content-Type-Options: nosniff
X-XSS-Protection: 0
Cache-Control: no-cache, no-store, max-age=0, must-revalidate
Pragma: no-cache
Expires: 0
X-Frame-Options: DENY
Content-Security-Policy: default-src 'none'; frame-ancestors 'none'
Content-Type: application/json
Content-Length: 156

{
  "id": "ffdcf57c-d47f-4e41-87bf-42a7de1203c0",
  "postId": 1,
  "author": "asha",
  "text": "Try the scampi at Mahesh Lunch Home",
  "createdAt": "2026-10-13T14:03:19.277Z"
}
```

### Case 7: a muted user

**Why:** Tara is signed in but muted: `403`.

Request

``` code
POST /posts/1/comments HTTP/1.1
Authorization: Basic dGFyYTp0YXJhLWRlbW8tcGFzcw==
Content-Type: application/json

{
  "text": "Let me in"
}
```

Response

``` code
HTTP/1.1 403 
X-Content-Type-Options: nosniff
X-XSS-Protection: 0
Cache-Control: no-cache, no-store, max-age=0, must-revalidate
Pragma: no-cache
Expires: 0
X-Frame-Options: DENY
Content-Security-Policy: default-src 'none'; frame-ancestors 'none'
Content-Type: application/problem+json
Content-Length: 169

{
  "type": "https://chaupal.example/problems/forbidden",
  "title": "Not allowed",
  "status": 403,
  "detail": "Your account cannot do this right now.",
  "instance": "/posts/1/comments"
}
```

### Case 8: Asha opens Ravi's private post

**Why:** `404`, as for a post that does not exist.

Request

``` code
GET /posts/2/comments HTTP/1.1
Authorization: Basic YXNoYTphc2hhLWRlbW8tcGFzcw==
```

Response

``` code
HTTP/1.1 404 
X-Content-Type-Options: nosniff
X-XSS-Protection: 0
Cache-Control: no-cache, no-store, max-age=0, must-revalidate
Pragma: no-cache
Expires: 0
X-Frame-Options: DENY
Content-Security-Policy: default-src 'none'; frame-ancestors 'none'
Content-Type: application/problem+json

{
  "detail": "No post with this id is visible to you.",
  "instance": "/posts/2/comments",
  "status": 404,
  "title": "Post not found",
  "type": "https://chaupal.example/problems/post-not-found"
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                                                              | What the API does                                               | Proved by                                                        |
|---------------------------------------------------------------------------------------------------|-----------------------------------------------------------------|------------------------------------------------------------------|
| Seven common XSS payloads (script, upper-case script, nested, img, svg, iframe, javascript: link) | Stored as typed; shown in HTML as exactly `htmlEscape(payload)` | `everyPayloadIsStoredAsTextAndShownAsText` (7 cases)             |
| `<b>`, `&`, double and single quotes                                                              | All encoded; CSP header present                                 | `theHtmlFragmentEncodesEveryCharacterThatMatters`                |
| JSON list                                                                                         | Oldest first, text unchanged                                    | `jsonListsCommentsOldestFirstWithTheTextExactlyAsTyped`          |
| "ＩＤＩＯＴ", "1d10t", "\$c@m", "s c a m", "stuuupid", "id-iot"                                   | Caught                                                          | `disguisesAreSeenThrough`, `aBannedWordIs422WithoutRepeatingIt`  |
| "scampi", "smart idea"                                                                            | Allowed                                                         | `wholeWordsOnlySoScampiIsFine`                                   |
| "stupidity", "st\*pid"                                                                            | Allowed: known limits of a word list                            | `theLimitsOfAWordList`                                           |
| Turkish server locale                                                                             | Still caught                                                    | `aTurkishServerLocaleChangesNothing`                             |
| Blank, 501 characters; exactly 500                                                                | `400`; `201`                                                    | `blankOrTooLongTextIs400`                                        |
| Sixth comment in a minute                                                                         | `429` + `Retry-After`; other users unaffected                   | `theSixthCommentInAMinuteIs429WithRetryAfter`                    |
| No login; muted user                                                                              | `401`; `403`                                                    | `postingWithoutSigningInIs401`, `aMutedUserCanReadButNotPost403` |
| Another user's private post                                                                       | `404` to read or post                                           | `anotherUsersPrivatePostLooksLikeItDoesNotExist`                 |
| `author` in the body                                                                              | Ignored                                                         | `anAuthorFieldInTheBodyIsIgnored`                                |
| Refused payload                                                                                   | Not echoed in the error                                         | `aRefusedPayloadIsNotEchoedInTheError`                           |
| Unknown post; broken JSON                                                                         | `404`; `400`                                                    | `anUnknownPostIs404`, `brokenJsonIs400`                          |

## The trap

Plausible but wrong

Filtering `<script>` from input instead of encoding output; attackers bypass the filter.

A "before" controller removes `<script>` and `</script>` from every comment, then builds HTML by gluing strings. The first test posts two classic payloads: the `<img onerror>` passes untouched, and `<scr<script>ipt>` becomes a working `<script>` *because of* the filter. The second test sends the same payloads to the real API: both come out as harmless text.

``` code
package com.chaupal.comments;

import org.junit.jupiter.api.Test;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.security.Principal;
import java.util.stream.Collectors;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/**
 * The first test written for this station: it reproduces the attack before the fix.
 * Two well-known payloads against a "remove the script tags from the input" defence.
 */
@Import(InputFilterTrapTest.FilteringController.class)
class InputFilterTrapTest extends ApiTest {

    static final String IMG = "<img src=x onerror=alert(document.cookie)>";
    static final String NESTED = "<scr<script>ipt>alert(1)</script>";

    /** The "before" code: strip <script> tags on the way in, then put the text into HTML as-is. Kept only in tests. */
    @RestController
    static class FilteringController {
        private final CommentService service;

        FilteringController(CommentService service) {
            this.service = service;
        }

        @PostMapping("/naive/posts/{postId}/comments")
        Comment add(Principal user, @PathVariable long postId, @RequestBody CommentRequest r) {
            String cleaned = r.text().replaceAll("(?i)<script>", "").replaceAll("(?i)</script>", "");
            return service.add(user.getName(), postId, cleaned);
        }

        @GetMapping(value = "/naive/posts/{postId}/comments", produces = MediaType.TEXT_HTML_VALUE)
        String html(Principal user, @PathVariable long postId) {
            return service.list(postId, user.getName()).stream()
                    .map(c -> "<li><b>" + c.author() + "</b> <p>" + c.text() + "</p></li>")
                    .collect(Collectors.joining("\n", "<ul>\n", "\n</ul>"));
        }
    }

    @Test
    void theFilterMissesAnImageTagAndRebuildsTheScriptTagItRemoved() throws Exception {
        for (String payload : new String[]{IMG, NESTED}) {
            mvc.perform(post("/naive/posts/1/comments").with(httpBasic("ravi", "ravi-demo-pass"))
                    .contentType(MediaType.APPLICATION_JSON).content(body(payload)));
        }
        String page = mvc.perform(get("/naive/posts/1/comments").with(httpBasic("asha", "asha-demo-pass")).accept(MediaType.TEXT_HTML))
                .andReturn().getResponse().getContentAsString();
        assertThat(page).contains("<img src=x onerror=alert(document.cookie)>"); // not a <script>, so the filter ignores it
        assertThat(page).contains("<script>alert(1)");                           // removing the inner tag joined the outer one
    }

    @Test
    void encodingOnOutputTurnsBothIntoHarmlessText() throws Exception {
        comment("ravi", 1, IMG);
        comment("ravi", 1, NESTED);
        String page = html(1);
        assertThat(page).contains("&lt;img src=x onerror=alert(document.cookie)&gt;");
        assertThat(page).contains("&lt;scr&lt;script&gt;ipt&gt;alert(1)&lt;/script&gt;");
        assertThat(page).doesNotContain("<img").doesNotContain("<script").doesNotContain("<scr<");
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
./mvnw test                 # all 27 tests
```

**Windows (PowerShell)**

``` code
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Demo users: `asha`, `ravi`, `kabir` (members) and `tara` (muted); each password is the name plus `-demo-pass`. The attack body is in `docs/attack.json`.

``` code
# Post the attack: expect 201
curl -i -u kabir:kabir-demo-pass -X POST http://localhost:8080/posts/1/comments -H "Content-Type: application/json" -d "@docs/attack.json"

# See it as HTML: expect &lt;img ... &gt; and a Content-Security-Policy header
curl -i -H "Accept: text/html" http://localhost:8080/posts/1/comments
```

Save the HTML answer as `comments.html` and open it in a browser: you see the attack as text, and no alert appears.

## Troubleshooting

| You see                            | Cause                                         | Fix                                                      |
|------------------------------------|-----------------------------------------------|----------------------------------------------------------|
| JSON when you wanted HTML          | No `Accept: text/html` header.                | Add `-H "Accept: text/html"`.                            |
| `429`                              | More than 5 comments in a minute as one user. | Wait 60 seconds or use another demo user.                |
| `release version 25 not supported` | Maven is using an older JDK.                  | Point `JAVA_HOME` at JDK 25, or add `-Djava.version=21`. |

## Project layout

``` tree
stations/007-comment-moderation-and-xss-safe-output/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/chaupal/comments/
│   ├── SecurityConfig.java   ├── CommentController.java   ├── CommentRequest.java
│   ├── CommentService.java   ├── Moderation.java          ├── RateLimiter.java
│   ├── CommentHtml.java      ├── ApiErrors.java           ├── ProblemResponses.java
│   └── Post.java, Comment.java, Exceptions.java, CommentsApplication.java
├── src/test/java/com/chaupal/comments/   (see Tests)
├── review/                   the flawed version (see Review)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels: security filters, controller, service, and the HTML on the way out.

#### `src/main/java/com/chaupal/comments/SecurityConfig.java`

Does  
Lets anyone read, members post, muted users only read; adds the Content-Security-Policy header.

Why  
Access rules live in one place, and CSP is a second wall if encoding is ever missed.

Without it  
Anyone could post; a single missed `htmlEscape` would run scripts.

#### `src/main/java/com/chaupal/comments/CommentController.java`

Does  
One `POST`, and one `GET` URL with two formats chosen by `Accept`: JSON or HTML.

Why  
The same data, two outputs: each output is responsible for its own safety.

Without it  
No API.

- `produces` on each `@GetMapping` lets Spring pick by the request's `Accept` header.

#### `src/main/java/com/chaupal/comments/CommentRequest.java`

Does  
Validates input: required and at most 500 characters. No author field.

Why  
Validation checks what input *is*, not whether it looks dangerous.

Without it  
Empty or huge comments.

#### `src/main/java/com/chaupal/comments/CommentService.java`

Does  
Checks the post is visible, runs moderation and the rate limit, stores the text exactly as typed.

Why  
Storing the original keeps every output free to encode for its own format (HTML, JSON, CSV, an email).

Without it  
Rules spread around; a filtered copy that is neither the original nor safe.

#### `src/main/java/com/chaupal/comments/Moderation.java`

Does  
Normalises text step by step, then compares whole words with a small list.

Why  
Disguises are undone before matching; whole words avoid blocking "scampi".

Without it  
"1d10t" passes and "scampi" is blocked (see Review).

- NFKC turns full-width `ＩＤＩＯＴ` into `IDIOT`.
- Runs of one-letter words are joined: `s c a m`.
- Three or more repeats collapse: `stuuupid`.

#### `src/main/java/com/chaupal/comments/RateLimiter.java`

Does  
Keeps each user's recent comment times and refuses a sixth within 60 seconds.

Why  
Limits the damage of spam bots and angry bursts.

Without it  
One account can flood a post.

#### `src/main/java/com/chaupal/comments/CommentHtml.java`

Does  
Builds the HTML fragment, passing every piece of user text through `htmlEscape`.

Why  
This is the one place where text becomes HTML, so it is the one place that must encode.

Without it  
The attack in case 2 runs in every reader's browser.

#### `src/main/java/com/chaupal/comments/ApiErrors.java`

The problem shape from station 006: 404, 422, 429 with `Retry-After`, and validation errors that never repeat input.

#### `src/main/java/com/chaupal/comments/ProblemResponses.java`

401 and 403 in the same problem shape (from station 006).

#### `src/main/java/com/chaupal/comments/Post.java`

A post and who may see it.

#### `src/main/java/com/chaupal/comments/Comment.java`

A stored comment.

#### `src/main/java/com/chaupal/comments/Exceptions.java`

Post not found, community rules, too many comments.

# 2 · Build: Tests

## Required tests for this station

Station type: Security

| Required by   | Requirement                                    | Test class                 | Result |
|---------------|------------------------------------------------|----------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found       | `CommentContractTest` (8)  | pass   |
| Every station | Reproduce the failure before the fix           | `InputFilterTrapTest` (2)  | pass   |
| Security      | 401, 403, another user's data, malicious input | `CommentSecurityTest` (12) | pass   |
| This station  | Normalising and matching on its own            | `ModerationTest` (5)       | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1, Spring Security 7. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.chaupal.comments.InputFilterTrapTest
[INFO] Tests run: 12, Failures: 0, Errors: 0, Skipped: 0 -- in com.chaupal.comments.CommentSecurityTest
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.chaupal.comments.ModerationTest
[INFO] Tests run: 8, Failures: 0, Errors: 0, Skipped: 0 -- in com.chaupal.comments.CommentContractTest
[INFO] Tests run: 27, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/chaupal/comments/InputFilterTrapTest.java`

Written first: the input filter misses one payload and builds another.

#### `src/test/java/com/chaupal/comments/CommentSecurityTest.java`

401, 403, private posts, the author field, seven payloads, and no echo in errors.

#### `src/test/java/com/chaupal/comments/CommentContractTest.java`

Post, JSON, HTML with CSP, length, moderation, rate limit, 404, broken JSON.

#### `src/test/java/com/chaupal/comments/ModerationTest.java`

Disguises caught, innocent words left alone, the honest limits, and a Turkish locale.

#### `src/test/java/com/chaupal/comments/ApiTest.java`

Shared setup: no comments and a fresh rate limit before each test; bodies built by Jackson so payloads arrive exactly.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/chaupal/comments/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=BoldFormattingChallengeTest`
3.  Change the code until it passes, then run `./mvnw test` to check the other 27 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 35 tests pass (27 station tests and 8 challenge tests).

Challenge 1 · Go deeper · about 30 minutes

## Safe bold text

Members want `**bold**`. In the HTML fragment, turn `**text**` into `<strong>text</strong>`, while every other tag the user typed stays encoded, including one inside the stars.

**Done when:** all four tests in `BoldFormattingChallengeTest` pass, and the station's tests still pass.

Hints

- Order matters: encode first, then format. After encoding, the only tag in the text can be the one you add.
- `*` is not changed by HTML encoding, so the stars are still there to find.
- A regular expression with a lazy group, `\*\*(…*?)\*\*`, finds each pair.

#### `challenge/BoldFormattingChallengeTest.java`

``` code
package com.chaupal.comments;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/** Challenge 1: **bold** becomes <strong>bold</strong> in the HTML, without opening a door for any other tag. */
class BoldFormattingChallengeTest extends ApiTest {

    private String shown(String text) throws Exception {
        comment("ravi", 1, text);
        return html(1).replaceAll("(?s).*<p>(.*)</p>.*", "$1");
    }

    @Test
    void doubleStarsBecomeStrong() throws Exception {
        assertThat(shown("**Amruttulya** is the best")).isEqualTo("<strong>Amruttulya</strong> is the best");
    }

    @Test
    void realTagsStayEncodedNextToTheFormatting() throws Exception {
        assertThat(shown("**yes** <b>no</b>")).isEqualTo("<strong>yes</strong> &lt;b&gt;no&lt;/b&gt;");
    }

    @Test
    void anAttackInsideTheStarsIsStillText() throws Exception {
        assertThat(shown("**<img src=x onerror=alert(1)>**")).isEqualTo("<strong>&lt;img src=x onerror=alert(1)&gt;</strong>");
    }

    @Test
    void unmatchedStarsStayAsTyped() throws Exception {
        assertThat(shown("5 ** 2 is not bold")).isEqualTo("5 ** 2 is not bold");
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 40 minutes

## Report a comment

Add `POST /posts/{postId}/comments/{commentId}/reports` for members: `204` each time. When 3 different members have reported a comment, it is hidden from both lists. Reporting twice counts once; an unknown comment or an invisible post is `404`; muted users get `403`.

**Done when:** all four tests in `ReportChallengeTest` pass.

Hints

- A `Set` of reporters per comment makes "twice counts once" automatic.
- Hide in `list()`, so JSON and HTML agree.
- Always `204`: telling a reporter "that was the third report" helps people coordinate to hide comments they dislike.

#### `challenge/ReportChallengeTest.java`

``` code
package com.chaupal.comments;

import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.ResultActions;

import java.util.UUID;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 2: members report a comment; three different reporters hide it. */
class ReportChallengeTest extends ApiTest {

    ResultActions report(String user, long postId, String commentId) throws Exception {
        return mvc.perform(post("/posts/{p}/comments/{c}/reports", postId, commentId).with(httpBasic(user, user + "-demo-pass")));
    }

    String commentId(String user, long postId, String text) throws Exception {
        String json = comment(user, postId, text).andReturn().getResponse().getContentAsString();
        return com.jayway.jsonpath.JsonPath.read(json, "$.id");
    }

    @Test
    void threeDifferentReportersHideTheComment() throws Exception {
        String id = commentId("ravi", 1, "Visit my shop for cheap phones");
        report("asha", 1, id).andExpect(status().isNoContent());
        report("kabir", 1, id).andExpect(status().isNoContent());
        mvc.perform(get("/posts/1/comments")).andExpect(jsonPath("$[0].id").value(id));   // two reports: still shown
        report("ravi", 1, id).andExpect(status().isNoContent());
        mvc.perform(get("/posts/1/comments")).andExpect(jsonPath("$").isEmpty());
    }

    @Test
    void reportingTwiceCountsOnce() throws Exception {
        String id = commentId("ravi", 1, "Hmm");
        report("asha", 1, id);
        report("asha", 1, id).andExpect(status().isNoContent());
        report("asha", 1, id);
        mvc.perform(get("/posts/1/comments")).andExpect(jsonPath("$[0].id").value(id));
    }

    @Test
    void anUnknownCommentOrAnInvisiblePostIs404() throws Exception {
        report("asha", 1, UUID.randomUUID().toString()).andExpect(status().isNotFound());
        String hidden = commentId("ravi", 2, "private note");
        report("asha", 2, hidden).andExpect(status().isNotFound());
    }

    @Test
    void mutedUsersCannotReport() throws Exception {
        String id = commentId("ravi", 1, "Hello");
        report("tara", 1, id).andExpect(status().isForbidden());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Links in comments

Members want links to be clickable. Which URLs would you allow (think of `javascript:` and `data:`)? Where in the encode-then-format order does linking happen? Which attributes would you add to the `<a>` tag, and why? When would you use a tested HTML sanitiser library instead of your own rules?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: the input filter misses `<img onerror>` and builds a `<script>`.
2.  Store text as typed; encode in the one place that writes HTML.
3.  Add CSP as a second wall.
4.  Write `Moderation.words` step by step, with a test per disguise and per innocent word.
5.  Add length and rate limits, each with its own status code.

## Design alternatives and trade-offs

| Approach                                                           | What it costs                                                                   | Verdict              |
|--------------------------------------------------------------------|---------------------------------------------------------------------------------|----------------------|
| Store as typed, encode on output                                   | Every output path must encode for its own format.                               | Chosen               |
| Blocklist filter on input                                          | Bypassed by other tags, case tricks and nesting; damages honest text.           | Wrong                |
| HTML-encode on input, store encoded                                | JSON and CSV now show `&lt;`; encoding twice shows `&amp;lt;`.                  | Wrong                |
| A sanitiser library allowing some tags (OWASP Java HTML Sanitizer) | The right choice when users need real formatting. A dependency to keep updated. | When needed          |
| Substring match for banned words                                   | Blocks "scampi"; misses "1d10t".                                                | Wrong                |
| Hold suspicious comments for a moderator                           | Kinder than rejecting, slower to appear.                                        | Common in production |

## Database design

None in this station. With a database, store the original text in a `TEXT` column with a length check, and never store an "encoded" copy.

# 3 · Go deeper: Production

Security  
Encoding stops HTML injection; CSP stops scripts even if encoding is missed; JSON clients must render text as text. Encoding is per context: HTML text, an HTML attribute, a URL and JavaScript each need their own.

Abuse  
Moderation runs before the rate limit, so refused comments do not use up a user's 5; a determined spammer of banned words is limited only by the 422. Watch the 422 rate per user.

Scale  
The rate limit is per server. Several servers need a shared counter (Redis or a gateway), covered in later stations.

Maintainability  
The banned list is code here; in production it is data that moderators can edit, with tests for both "caught" and "allowed".

# 3 · Go deeper: Interview

## Interview takeaways

What is XSS, in one sentence?

An attacker gets their text into a page in a way that the browser runs it as code, with the reader's session.

Why encode output instead of filtering input?

A filter must know every dangerous input and fails on the one it missed; encoding needs no list: every special character is shown as itself. Filters also corrupt honest text.

Is JSON safe from XSS?

JSON itself is data. The danger is the client: inserting JSON text with innerHTML brings XSS back. Use textContent or a framework's default escaping.

What does a Content-Security-Policy add?

A second line of defence: the browser refuses to run scripts the policy does not allow, even if an attacker gets markup into the page.

Why normalise text before matching banned words?

Attackers use look-alikes: full-width letters, digits for letters, spaces between letters. Normalising maps them to one form so one list covers them; whole-word comparison avoids blocking innocent words.

422 or 400 for a banned word?

400 is for malformed requests. The request is well-formed; its content is not acceptable. 422 says exactly that.

## Self-check rubric

| Area        | Meets the bar                         | Above the bar                                                     |
|-------------|---------------------------------------|-------------------------------------------------------------------|
| Correctness | All 27 tests pass.                    | You can predict what the flawed version fails.                    |
| Security    | Every output of user text is encoded. | You can name the encoding for an attribute, a URL and JavaScript. |
| Design      | Store as typed, encode on output.     | You can explain why encode-then-format, not the reverse.          |
| Explanation | You can show the nested-tag bypass.   | You can explain the limits of any word list.                      |

# 3 · Go deeper: Review

## The pull request

A teammate's "security hardening" PR: sanitise on the way in, a simpler moderator, and a tidy-up of `list()`. Read the three files and list every problem before opening the findings.

#### `review/CommentService.java`

``` code
package com.chaupal.comments;

import org.springframework.stereotype.Service;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/** Posts and comments in memory. The rules: who can see a post, moderation, and the rate limit. */
@Service
class CommentService {

    private final Map<Long, Post> posts = Map.of(
            1L, new Post(1, "asha", "Best cutting chai in Pune?", false),
            2L, new Post(2, "ravi", "Notes to self", true));
    private final List<Comment> comments = new ArrayList<>();
    private final Moderation moderation;
    private final RateLimiter rateLimiter;

    CommentService(Moderation moderation, RateLimiter rateLimiter) {
        this.moderation = moderation;
        this.rateLimiter = rateLimiter;
    }

    /** Sanitise on the way in, so nothing dangerous is ever stored. */
    Comment add(String user, long postId, String text) {
        visiblePost(postId, user);
        text = text.replaceAll("(?i)<script[^>]*>.*?</script>", "");
        if (moderation.breaksRules(text)) {
            throw new Exceptions.BreaksCommunityRules();
        }
        if (!rateLimiter.tryAcquire(user)) {
            throw new Exceptions.TooManyComments();
        }
        var c = new Comment(UUID.randomUUID(), postId, user, text, Instant.now().truncatedTo(ChronoUnit.MILLIS));
        synchronized (comments) {
            comments.add(c);
        }
        return c;
    }

    /** user is null for a reader who is not signed in. */
    List<Comment> list(long postId, String user) {
        if (!posts.containsKey(postId)) {
            throw new Exceptions.PostNotFound();
        }
        synchronized (comments) {
            return comments.stream().filter(c -> c.postId() == postId).toList();
        }
    }

    private Post visiblePost(long postId, String user) {
        Post p = posts.get(postId);
        if (p == null || !p.visibleTo(user)) {
            throw new Exceptions.PostNotFound();
        }
        return p;
    }

    /** For tests only. */
    void clear() {
        synchronized (comments) {
            comments.clear();
        }
    }
}
```

#### `review/CommentHtml.java`

``` code
package com.chaupal.comments;

import java.util.List;

/** Comments as an HTML fragment. Text is already sanitised when it is saved (see CommentService), so no escaping needed here. */
final class CommentHtml {

    private CommentHtml() {
    }

    static String render(List<Comment> comments) {
        StringBuilder html = new StringBuilder("<ul class=\"comments\">\n");
        for (Comment c : comments) {
            html.append("  <li><b>").append(c.author()).append("</b> <p>").append(c.text()).append("</p></li>\n");
        }
        return html.append("</ul>\n").toString();
    }
}
```

#### `review/Moderation.java`

``` code
package com.chaupal.comments;

import org.springframework.stereotype.Component;

import java.util.Set;

/** Simple and fast: lower-case the text and look for each banned word. */
@Component
class Moderation {

    static final Set<String> BANNED = Set.of("idiot", "stupid", "scam");

    boolean breaksRules(String text) {
        String lower = text.toLowerCase();
        return BANNED.stream().anyMatch(lower::contains);
    }

    static java.util.List<String> words(String text) {
        return java.util.List.of(text.toLowerCase().split("\\s+"));
    }
}
```

## Findings

1"Sanitise on input" with a `<script>` regex

Only script tags are removed; `<img onerror>`, `<svg onload>` and others pass. It also damages honest comments: `<scr<script>ipt>…` was stored as `<scr`.

**Test evidence:** `everyPayloadIsStoredAsTextAndShownAsText`: the stored text differs from what was sent.

2No encoding in `CommentHtml`

"Already sanitised" is trusted, so every payload the filter missed reaches the page as live HTML.

**Test evidence:** `encodingOnOutputTurnsBothIntoHarmlessText`, `theHtmlFragmentEncodesEveryCharacterThatMatters` and the payload cases.

3Substring matching in `Moderation`

`text.toLowerCase().contains(word)` misses "1d10t" and "ＩＤＩＯＴ", blocks "scampi", and uses the server's locale.

**Test evidence:** `aBannedWordIs422WithoutRepeatingIt` (got 201), all five `ModerationTest` tests.

4Private posts readable by anyone

`list()` checks only that the post exists, not that the reader may see it. Posting is still blocked, which makes the gap easy to miss.

**Test evidence:** `anotherUsersPrivatePostLooksLikeItDoesNotExist`: 200 instead of 404.

## Same tests, flawed version

From `docs/review-run.txt`: the three flawed files copied over the real ones, then the full suite run.

| Test class            | Fixed version | Flawed version |
|-----------------------|---------------|----------------|
| `CommentContractTest` | 8 / 8         | 6 / 8          |
| `CommentSecurityTest` | 12 / 12       | 4 / 12         |
| `InputFilterTrapTest` | 2 / 2         | 1 / 2          |
| `ModerationTest`      | 5 / 5         | 0 / 5          |

The PR's own description says "security hardening". Every change made the API less safe. Reviews need tests that ask what an attacker would send, not just whether the happy path still works.
