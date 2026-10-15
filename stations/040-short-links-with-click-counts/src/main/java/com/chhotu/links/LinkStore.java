package com.chhotu.links;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

import java.time.OffsetDateTime;
import java.util.Optional;

@Repository
class LinkStore {

    /** Tries this many codes before giving up; with 7 characters even one retry is extremely rare. */
    static final int ATTEMPTS = 5;

    record Link(String code, String targetUrl, long clicks, OffsetDateTime createdAt) {
    }

    private final JdbcClient jdbc;
    private final CodeGenerator codes;

    LinkStore(JdbcClient jdbc, CodeGenerator codes) {
        this.jdbc = jdbc;
        this.codes = codes;
    }

    /**
     * Inserts with a fresh code. ON CONFLICT DO NOTHING turns a taken code into "0 rows", and we try another; the row
     * that already had the code is never touched. Empty only if every attempt collided.
     */
    Optional<String> create(String targetUrl) {
        for (int attempt = 0; attempt < ATTEMPTS; attempt++) {
            String code = codes.next();
            int inserted = jdbc.sql("INSERT INTO links (code, target_url) VALUES (:code, :url) ON CONFLICT (code) DO NOTHING")
                    .param("code", code).param("url", targetUrl).update();
            if (inserted == 1) {
                return Optional.of(code);
            }
        }
        return Optional.empty();
    }

    Optional<String> target(String code) {
        return jdbc.sql("SELECT target_url FROM links WHERE code = :code").param("code", code).query(String.class).optional();
    }

    Optional<Link> link(String code) {
        return jdbc.sql("SELECT code, target_url, clicks, created_at FROM links WHERE code = :code").param("code", code).query(Link.class).optional();
    }

    void addClicks(String code, long clicks) {
        jdbc.sql("UPDATE links SET clicks = clicks + :n WHERE code = :code").param("n", clicks).param("code", code).update();
    }
}
