package com.kartwala.export;

import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.asyncDispatch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;

/** Shared setup: the whole app on a real PostgreSQL, the demo orders exactly as V2 makes them, an empty export log. */
@SpringBootTest
@AutoConfigureMockMvc
@Import(PostgresTestConfig.class)
abstract class ApiTest {

    @Autowired
    MockMvc mvc;
    @Autowired
    JdbcClient jdbc;

    @BeforeEach
    void demoOrders() throws Exception {
        jdbc.sql("TRUNCATE orders, export_log RESTART IDENTITY").update();
        jdbc.sql(Files.readString(Path.of("src/main/resources/db/migration/V2__demo_orders.sql"))).update();
    }

    static String password(String user) {
        return user.substring(0, user.indexOf('.')) + "-demo-pass";
    }

    /** Runs the export; a streamed answer finishes on another thread, so MockMvc dispatches it again to read it. */
    MockHttpServletResponse export(String user, String from, String to) throws Exception {
        var request = get("/seller/orders/export").param("from", from).param("to", to);
        if (user != null) {
            request.with(httpBasic(user, password(user)));
        }
        MvcResult started = mvc.perform(request).andReturn();
        return started.getRequest().isAsyncStarted() ? mvc.perform(asyncDispatch(started)).andReturn().getResponse() : started.getResponse();
    }

    static List<String> lines(MockHttpServletResponse r) {
        String body = new String(r.getContentAsByteArray(), StandardCharsets.UTF_8);
        return List.of(body.substring(1).split("\r\n"));   // after the byte order mark
    }
}
