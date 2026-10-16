# Station 066 plan: Social feed with keyset pagination

**Problem.** Chaupal's feed paged with OFFSET: page 2,000 read and threw away 40,000 posts, and new posts pushed the
last posts of a page onto the next one, so readers saw repeats.

**Endpoint.** `GET /feed?cursor&limit`: limit 1-50 (default 20), newest first by (created_at, id). 200 {posts[{id,
author, body, createdAt}], nextCursor (null at the end)}. The cursor is base64url of "v1:<epoch micros>:<id>",
opaque, not a secret; anything else is 400. A cursor past the oldest post: an empty page.

**Query.** First page ORDER BY created_at DESC, id DESC LIMIT n+1; later pages WHERE (created_at, id) < (:t, :id)
with the same order; the extra row decides nextCursor (no count). Index posts_feed (created_at, id), read backwards.
Timestamps bound as OffsetDateTime in UTC.

**Database.** authors_handle_unique, authors_handle_shape, posts_author_fk, posts_body_not_blank, created_at default
now(). Demo: 4 authors, 100,000 posts, five per second (shared timestamps).

**Trap.** `OffsetPagingTrapTest`: page 2,000 by OFFSET reads >= 40,020 rows, keyset <= 100; 3 new posts repeat the
last 3 of page 1 at the top of OFFSET page 2, keyset continues at 99980; a cursor with the time alone skips the 4
posts that share the last post's second.

**Mutations.** time-only cursor -> 4; no index -> 1; lenient cursor parsing -> 1; no extra row -> 5.

**Practice.** 1: one author's feed with the same cursor. 2: pull to refresh (topCursor, posts newer than it).
3 (paper): a cursor that can be tampered with; signed or not.
