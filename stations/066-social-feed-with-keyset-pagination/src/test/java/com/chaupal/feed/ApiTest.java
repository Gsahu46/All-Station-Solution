package com.chaupal.feed;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.transaction.support.TransactionTemplate;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

import java.util.Map;

/**
 * Shared setup: the whole app on a real PostgreSQL with the demo feed: 100,000 posts, five per second, so every
 * timestamp is shared by five posts. Tests that add posts remove them again.
 */
@SpringBootTest
@AutoConfigureMockMvc
@Import(PostgresTestConfig.class)
abstract class ApiTest {

    @Autowired
    MockMvc mvc;
    @Autowired
    JdbcClient jdbc;
    @Autowired
    TransactionTemplate transaction;

    final JsonMapper json = JsonMapper.builder().build();

    /** Rows every scan in the plan really produced, from EXPLAIN ANALYZE, without parallel workers. */
    long rowsRead(String sql, Map<String, Object> params) {
        return transaction.execute(status -> {
            jdbc.sql("SET LOCAL max_parallel_workers_per_gather = 0").update();
            String plan = jdbc.sql("EXPLAIN (ANALYZE, FORMAT JSON) " + sql).params(params).query(String.class).single();
            return scanned(json.readTree(plan).get(0).get("Plan"));
        });
    }

    private static long scanned(JsonNode node) {
        long rows = node.get("Node Type").asString().contains("Scan") ? node.get("Actual Rows").asLong() * node.get("Actual Loops").asLong() : 0;
        if (node.has("Plans")) {
            for (JsonNode child : node.get("Plans")) {
                rows += scanned(child);
            }
        }
        return rows;
    }

    JsonNode getFeed(String cursor, int limit) throws Exception {
        var request = org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get("/feed").param("limit", String.valueOf(limit));
        if (cursor != null) {
            request.param("cursor", cursor);
        }
        return json.readTree(mvc.perform(request).andReturn().getResponse().getContentAsString());
    }

    void post(String body) {
        jdbc.sql("INSERT INTO posts (author_id, body, created_at) VALUES (1, ?, TIMESTAMPTZ '2026-10-02 00:00:00+00')").param(body).update();
    }
}
