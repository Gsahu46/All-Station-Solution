package com.tiffino.dishes;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.transaction.support.TransactionTemplate;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/** Shared setup: the whole app on a real PostgreSQL with the demo data (8 dishes written out, 200,000 generated). */
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

    /** What one run did: the plan's node types and indexes, and the 8 kB pages it touched (EXPLAIN ANALYZE, BUFFERS). */
    record Plan(List<String> nodes, List<String> indexes, long pages) {
    }

    Plan explain(String sql, Map<String, Object> params) {
        return transaction.execute(status -> {
            jdbc.sql("SET LOCAL max_parallel_workers_per_gather = 0").update();
            String plan = jdbc.sql("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + sql).params(params).query(String.class).single();
            JsonNode root = json.readTree(plan).get(0).get("Plan");
            List<String> nodes = new ArrayList<>();
            List<String> indexes = new ArrayList<>();
            walk(root, nodes, indexes);
            return new Plan(nodes, indexes, root.get("Shared Hit Blocks").asLong() + root.get("Shared Read Blocks").asLong());
        });
    }

    private static void walk(JsonNode node, List<String> nodes, List<String> indexes) {
        nodes.add(node.get("Node Type").asString());
        if (node.has("Index Name")) {
            indexes.add(node.get("Index Name").asString());
        }
        if (node.has("Plans")) {
            node.get("Plans").forEach(child -> walk(child, nodes, indexes));
        }
    }
}
