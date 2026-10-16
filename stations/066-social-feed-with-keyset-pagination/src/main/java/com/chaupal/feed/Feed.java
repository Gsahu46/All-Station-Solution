package com.chaupal.feed;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;

@Service
class Feed {

    record Post(long id, String author, String body, Instant createdAt) {
    }

    record Page(List<Post> posts, String nextCursor) {
    }

    static final String FIRST = """
            SELECT p.id, a.handle AS author, p.body, p.created_at FROM posts p JOIN authors a ON a.id = p.author_id
            ORDER BY p.created_at DESC, p.id DESC LIMIT :n""";

    /** Seek: start right after the cursor's post, in the index's order. No OFFSET, so no rows are read and thrown away. */
    static final String AFTER = """
            SELECT p.id, a.handle AS author, p.body, p.created_at FROM posts p JOIN authors a ON a.id = p.author_id
            WHERE (p.created_at, p.id) < (:createdAt, :id)
            ORDER BY p.created_at DESC, p.id DESC LIMIT :n""";

    private final JdbcClient jdbc;

    Feed(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    Page page(Cursor after, int limit) {
        // One row more than asked: if it exists, there is a next page, and no count is needed.
        List<Post> rows = (after == null ? jdbc.sql(FIRST)
                : jdbc.sql(AFTER).param("createdAt", OffsetDateTime.ofInstant(after.createdAt(), ZoneOffset.UTC)).param("id", after.id()))
                .param("n", limit + 1).query(Post.class).list();
        if (rows.size() <= limit) {
            return new Page(rows, null);
        }
        List<Post> page = rows.subList(0, limit);
        Post last = page.getLast();
        return new Page(page, new Cursor(last.createdAt(), last.id()).encode());
    }
}
