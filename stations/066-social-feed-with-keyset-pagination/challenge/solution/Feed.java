package com.chaupal.feed;

import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;

@Service
class Feed {

    record Post(long id, String author, String body, Instant createdAt) {
    }

    record Page(List<Post> posts, String nextCursor, String topCursor) {
        Page(List<Post> posts, String nextCursor) {
            this(posts, nextCursor, posts.isEmpty() ? null : new Cursor(posts.getFirst().createdAt(), posts.getFirst().id()).encode());
        }
    }

    static final String FIRST = """
            SELECT p.id, a.handle AS author, p.body, p.created_at FROM posts p JOIN authors a ON a.id = p.author_id
            ORDER BY p.created_at DESC, p.id DESC LIMIT :n""";

    /** Seek: start right after the cursor's post, in the index's order. No OFFSET, so no rows are read and thrown away. */
    static final String AFTER = """
            SELECT p.id, a.handle AS author, p.body, p.created_at FROM posts p JOIN authors a ON a.id = p.author_id
            WHERE (p.created_at, p.id) < (:createdAt, :id)
            ORDER BY p.created_at DESC, p.id DESC LIMIT :n""";

    /** Challenge 2: the posts after the cursor in time, oldest first, so the limit keeps the ones right after it. */
    static final String NEWER = """
            SELECT p.id, a.handle AS author, p.body, p.created_at FROM posts p JOIN authors a ON a.id = p.author_id
            WHERE (p.created_at, p.id) > (:createdAt, :id)
            ORDER BY p.created_at, p.id LIMIT :n""";

    private final JdbcClient jdbc;

    Feed(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    /** Challenge 1: the same seek, for one author. */
    Page page(Cursor after, int limit, String author) {
        if (author == null) {
            return page(after, limit);
        }
        Long authorId = jdbc.sql("SELECT id FROM authors WHERE handle = ?").param(author).query(Long.class).optional()
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "No author " + author));
        String sql = (after == null ? FIRST : AFTER).replace("ORDER BY", (after == null ? "WHERE" : "AND") + " p.author_id = :author ORDER BY");
        var spec = jdbc.sql(sql).param("author", authorId).param("n", limit + 1);
        if (after != null) {
            spec = spec.param("createdAt", OffsetDateTime.ofInstant(after.createdAt(), ZoneOffset.UTC)).param("id", after.id());
        }
        return toPage(spec.query(Post.class).list(), limit);
    }

    /** Challenge 2. */
    Page newer(Cursor since, int limit) {
        List<Post> rows = new java.util.ArrayList<>(jdbc.sql(NEWER).param("createdAt", OffsetDateTime.ofInstant(since.createdAt(), ZoneOffset.UTC))
                .param("id", since.id()).param("n", limit).query(Post.class).list());
        java.util.Collections.reverse(rows);   // newest first, like the feed
        return rows.isEmpty() ? new Page(rows, null, new Cursor(since.createdAt(), since.id()).encode()) : new Page(rows, null);
    }

    Page page(Cursor after, int limit) {
        // One row more than asked: if it exists, there is a next page, and no count is needed.
        List<Post> rows = (after == null ? jdbc.sql(FIRST)
                : jdbc.sql(AFTER).param("createdAt", OffsetDateTime.ofInstant(after.createdAt(), ZoneOffset.UTC)).param("id", after.id()))
                .param("n", limit + 1).query(Post.class).list();
        return toPage(rows, limit);
    }

    private static Page toPage(List<Post> rows, int limit) {
        if (rows.size() <= limit) {
            return new Page(rows, null);
        }
        List<Post> page = rows.subList(0, limit);
        Post last = page.getLast();
        return new Page(page, new Cursor(last.createdAt(), last.id()).encode());
    }
}
