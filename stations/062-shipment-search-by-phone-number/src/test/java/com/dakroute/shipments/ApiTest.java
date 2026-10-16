package com.dakroute.shipments;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.transaction.support.TransactionTemplate;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

/**
 * Shared setup: the whole app on a real PostgreSQL with the demo data (300,003 shipments). Plans are read from
 * EXPLAIN (ANALYZE, BUFFERS): pages read and node types, never timings, so the assertions are stable.
 */
@SpringBootTest
@AutoConfigureMockMvc
@Import(PostgresTestConfig.class)
abstract class ApiTest {

    static final String CUSTOMER = "9876543210";
    static final String SELLER = "9123456789";

    @Autowired
    MockMvc mvc;
    @Autowired
    JdbcClient jdbc;
    @Autowired
    TransactionTemplate transaction;

    final JsonMapper json = JsonMapper.builder().build();

    /** What one run of a query did: every node type and index in its plan, the index entries it returned, and the 8 kB pages it touched. */
    record Plan(List<String> nodes, List<String> indexes, long indexRows, long pages) {
    }

    /** The app's search, run on {@code table} under EXPLAIN ANALYZE, without parallel workers. */
    Plan explainSearch(String table, String phone, LocalDate from, LocalDate to) {
        return explain(ShipmentSearch.SQL.replace("FROM shipments", "FROM " + table), phone, from, to);
    }

    Plan explain(String sql, String phone, LocalDate from, LocalDate to) {
        return transaction.execute(status -> {
            jdbc.sql("SET LOCAL max_parallel_workers_per_gather = 0").update();
            String plan = jdbc.sql("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + sql)
                    .param("phone", phone).param("from", from).param("to", to).param("limit", ShipmentSearch.LIMIT).query(String.class).single();
            JsonNode root = json.readTree(plan).get(0).get("Plan");
            List<String> nodes = new ArrayList<>();
            List<String> indexes = new ArrayList<>();
            long indexRows = walk(root, nodes, indexes);
            return new Plan(nodes, indexes, indexRows, root.get("Shared Hit Blocks").asLong() + root.get("Shared Read Blocks").asLong());
        });
    }

    private static long walk(JsonNode node, List<String> nodes, List<String> indexes) {
        nodes.add(node.get("Node Type").asString());
        long indexRows = 0;
        if (node.has("Index Name")) {
            indexes.add(node.get("Index Name").asString());
            indexRows = node.get("Actual Rows").asLong() * node.get("Actual Loops").asLong();
        }
        if (node.has("Plans")) {
            for (JsonNode child : node.get("Plans")) {
                indexRows += walk(child, nodes, indexes);
            }
        }
        return indexRows;
    }
}
