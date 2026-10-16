package com.kartwala.attributes;

import org.junit.jupiter.api.AfterEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;
import org.springframework.transaction.support.TransactionTemplate;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/** Shared setup: the whole app on a real PostgreSQL with 6 hand-written and 60,000 generated products. Test SKUs start with T- and are removed. */
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

    @AfterEach
    void removeTestProducts() {
        jdbc.sql("DELETE FROM products WHERE sku LIKE 'T-%'").update();
    }

    ResultActions create(String body) throws Exception {
        return mvc.perform(post("/products").contentType(MediaType.APPLICATION_JSON).content(body));
    }

    /** Index names in the plan of a query, from EXPLAIN (FORMAT JSON). */
    List<String> indexesUsed(String sql, Map<String, Object> params) {
        String plan = jdbc.sql("EXPLAIN (FORMAT JSON) " + sql).params(params).query(String.class).single();
        List<String> names = new ArrayList<>();
        collect(json.readTree(plan).get(0).get("Plan"), names);
        return names;
    }

    private static void collect(JsonNode node, List<String> names) {
        if (node.has("Index Name")) {
            names.add(node.get("Index Name").asString());
        }
        if (node.has("Plans")) {
            node.get("Plans").forEach(child -> collect(child, names));
        }
    }
}
