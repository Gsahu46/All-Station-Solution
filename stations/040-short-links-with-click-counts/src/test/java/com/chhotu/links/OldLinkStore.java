package com.chhotu.links;

import org.springframework.jdbc.core.simple.JdbcClient;

/**
 * The link store before the fix, kept only in tests: 4-character codes, a table with no key on the code, and a
 * "save" that updates the row if the code exists, else inserts. A collision silently replaces the earlier link.
 */
final class OldLinkStore {

    private OldLinkStore() {
    }

    static void createTable(JdbcClient jdbc) {
        jdbc.sql("DROP TABLE IF EXISTS old_links").update();
        jdbc.sql("CREATE TABLE old_links (code VARCHAR(4), target_url TEXT)").update();   // no primary key, no unique
    }

    static void save(JdbcClient jdbc, String code, String targetUrl) {
        int updated = jdbc.sql("UPDATE old_links SET target_url = ? WHERE code = ?").params(targetUrl, code).update();
        if (updated == 0) {
            jdbc.sql("INSERT INTO old_links (code, target_url) VALUES (?, ?)").params(code, targetUrl).update();
        }
    }

    static String target(JdbcClient jdbc, String code) {
        return jdbc.sql("SELECT target_url FROM old_links WHERE code = ?").param(code).query(String.class).single();
    }

    /** The birthday problem: chance that n random codes out of `space` contain at least one repeat. */
    static double chanceOfARepeat(long n, double space) {
        return 1 - Math.exp(-(double) n * (n - 1) / (2 * space));
    }
}
