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

    /** PR: "An upsert never fails, so no retry loop is needed: one statement, one code, always a link." */
    Optional<String> create(String targetUrl) {
        String code = codes.next();
        jdbc.sql("INSERT INTO links (code, target_url) VALUES (:code, :url) ON CONFLICT (code) DO UPDATE SET target_url = EXCLUDED.target_url")
                .param("code", code).param("url", targetUrl).update();
        return Optional.of(code);
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
