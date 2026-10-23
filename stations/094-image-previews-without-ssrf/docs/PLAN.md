# Station 094 plan: Image previews without SSRF

**Problem.** Chaupal (fictional community app): "preview this link" fetched any URL. An attacker sent the cloud
metadata address (169.254.169.254) and read the instance's keys in the preview. A later fix checked the name's
address and then fetched, and a name that answered differently the second time (DNS rebinding) walked through.

**Endpoints.** `POST /link-previews` {url}: 201 with id, url, title (og:title or <title>), description, imageUrl
(og:image, absolute, http/https only, linked not fetched); not http/https, no host, or user info 400; a blocked
address, no such host, not HTML, not 200, a bad or endless redirect 422; slower than 3 s 504. `GET
/link-previews/{id}`: the member's own preview; anyone else's 404. HTTP Basic: members meera, dev; guest 403.

**Fetching.** Apache HttpClient 5 with our DnsResolver: every name (also on redirects, also IP literals) is resolved
once by us; if any address is blocked the request fails; the connection goes to exactly those addresses. Connect 2 s,
read 3 s, at most 3 redirects, the first 512 KB only (then the request is cancelled), text/html only.

**Blocked.** Loopback, private (10/8, 172.16/12, 192.168/16), link-local (169.254/16, fe80::/10), any-local, 0/8,
100.64/10, multicast, fc00::/7. A test-only list allows 127.0.0.2 (the test "public" site).

**Trap.** `FetchAnyUrlTrapTest`: openStream() on the internal address reads the secret; check-then-fetch is fooled by
rebind.example; the API refuses metadata.internal and fetches rebind.example from the checked public address, with one
lookup.

**Found while building.** (1) A huge page timed out instead of stopping at 512 KB: after the handler returns, the
client reads the rest to reuse the connection. Cancelling the request when more is coming fixed it. (2) A redirect to
file: came back as a 502 (a protocol error); mapped to 422. (3) The IPv4-mapped IPv6 check changed no test: Java turns
::ffff:a.b.c.d into an IPv4 address itself. Removed.

**Mutations.** no address check -> 2; first address only -> 1; no link-local -> 2; no CGNAT -> 2; no ULA -> 2; no
scheme check -> 1; user info allowed -> 1; no size cap -> 1; no cancel -> 1; long timeouts -> 1; no type check -> 1;
any owner -> 1.

**Review.** A string block-list of hosts and no check in the resolver: 2 of 12 fail.

**Practice.** 1: an allow-list of domains. 2: an image proxy through the same fetcher. 3 (paper): an egress proxy.
