package com.kartwala.prices;

import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;

/** Shared setup: the whole app on a real PostgreSQL; before each test the demo catalogue and its import revision, as V2 makes them. */
@SpringBootTest
@AutoConfigureMockMvc
@Import(PostgresTestConfig.class)
abstract class ApiTest {

    @Autowired
    MockMvc mvc;
    @Autowired
    JdbcClient jdbc;

    @BeforeEach
    void demoCatalogue() throws Exception {
        // TRUNCATE is not stopped by the append-only row triggers (see V1): only the table owner, here the tests, can do it.
        jdbc.sql("TRUNCATE products, products_aud, revisions RESTART IDENTITY").update();
        jdbc.sql(Files.readString(Path.of("src/main/resources/db/migration/V2__demo_catalogue.sql"))).update();
    }

    /** Demo users sign in as e.g. neha.store with neha-demo-pass. */
    static String password(String user) {
        return user.substring(0, user.indexOf('.')) + "-demo-pass";
    }

    ResultActions setPrice(String user, Object id, String json) throws Exception {
        return mvc.perform(put("/products/{id}/price", id).with(httpBasic(user, password(user))).contentType(MediaType.APPLICATION_JSON).content(json));
    }

    ResultActions setPrice(String user, Object id, long paise) throws Exception {
        return setPrice(user, id, "{\"pricePaise\":" + paise + "}");
    }

    ResultActions history(String user, Object id) throws Exception {
        return mvc.perform(get("/products/{id}/history", id).with(httpBasic(user, password(user))));
    }
}
