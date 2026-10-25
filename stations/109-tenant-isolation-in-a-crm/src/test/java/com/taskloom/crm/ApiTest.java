package com.taskloom.crm;

import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/**
 * The whole app on a real PostgreSQL. The tests' own JdbcClient connects as the container's superuser, which the
 * row-level policy does not bind: that is how they look at every tenant's rows, and how the old code ran.
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
    void onlyTheDemoLeads() {
        jdbc.sql("DELETE FROM leads WHERE id > 4").update();
    }

    ResultActions list(String user, String query) throws Exception {
        return mvc.perform(get("/leads" + query).with(httpBasic(user, user + "-demo-pass")));
    }

    /** GET /leads?q=..., the text sent exactly as given. */
    ResultActions searchFor(String user, String q) throws Exception {
        return mvc.perform(get("/leads").param("q", q).with(httpBasic(user, user + "-demo-pass")));
    }

    ResultActions create(String user, String json) throws Exception {
        return mvc.perform(post("/leads").with(httpBasic(user, user + "-demo-pass")).contentType(MediaType.APPLICATION_JSON).content(json));
    }

    String tenantOf(String email) {
        return String.join(",", jdbc.sql("SELECT tenant_id FROM leads WHERE email = ? ORDER BY tenant_id").param(email).query(String.class).list());
    }
}
