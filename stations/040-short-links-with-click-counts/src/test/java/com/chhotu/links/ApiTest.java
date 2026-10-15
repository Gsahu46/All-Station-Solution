package com.chhotu.links;

import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/** Shared setup: the app on a real PostgreSQL, no links and no buffered clicks before each test. */
@SpringBootTest(properties = "chhotu.clicks.flush-ms=3600000")   // tests flush by hand, so counts are exact
@AutoConfigureMockMvc
@Import(PostgresTestConfig.class)
abstract class ApiTest {

    @Autowired
    MockMvc mvc;
    @Autowired
    JdbcClient jdbc;
    @Autowired
    LinkStore links;
    @Autowired
    ClickCounter clicks;

    @BeforeEach
    void noLinks() {
        clicks.flush();
        jdbc.sql("TRUNCATE links").update();
    }

    ResultActions create(String targetUrl) throws Exception {
        return mvc.perform(post("/links").contentType(MediaType.APPLICATION_JSON).content("{\"targetUrl\":\"" + targetUrl + "\"}"));
    }

    ResultActions follow(String code) throws Exception {
        return mvc.perform(get("/" + code));
    }

    long storedClicks(String code) {
        return jdbc.sql("SELECT clicks FROM links WHERE code = ?").param(code).query(Long.class).single();
    }

    String targetOf(String code) {
        return jdbc.sql("SELECT target_url FROM links WHERE code = ?").param(code).query(String.class).single();
    }
}
