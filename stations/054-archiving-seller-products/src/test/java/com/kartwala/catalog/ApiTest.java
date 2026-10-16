package com.kartwala.catalog;

import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;

/**
 * Shared setup: the app on a real PostgreSQL with the demo catalogue, nothing archived. Seller 1 sells Assam tea (1)
 * and masala chai mix (2), both in past order KW-1001; seller 2 sells Kashmiri chilli (3).
 */
@SpringBootTest
@AutoConfigureMockMvc
@Import(PostgresTestConfig.class)
abstract class ApiTest {

    @Autowired
    MockMvc mvc;
    @Autowired
    JdbcClient jdbc;

    @BeforeEach
    void demoCatalogue() {
        jdbc.sql("DELETE FROM order_lines WHERE order_ref <> 'KW-1001'").update();
        jdbc.sql("DELETE FROM products WHERE id > 3").update();
        jdbc.sql("UPDATE products SET archived_at = NULL, updated_at = created_at").update();
    }

    ResultActions archive(long seller, long product) throws Exception {
        return mvc.perform(delete("/seller/products/{id}", product).header("X-Seller-Id", seller));
    }

    ResultActions list(long seller, String includeArchived) throws Exception {
        var request = get("/seller/products").header("X-Seller-Id", seller);
        return mvc.perform(includeArchived == null ? request : request.param("includeArchived", includeArchived));
    }

    long linesOfOrder(String ref) {
        return jdbc.sql("SELECT count(*) FROM order_lines WHERE order_ref = ?").param(ref).query(Long.class).single();
    }
}
