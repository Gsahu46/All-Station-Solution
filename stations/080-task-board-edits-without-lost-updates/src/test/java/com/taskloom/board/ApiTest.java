package com.taskloom.board;

import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;
import org.springframework.test.web.servlet.request.MockHttpServletRequestBuilder;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;

/** Shared setup: the whole app on a real PostgreSQL; before each test the demo board exactly as V2 creates it. */
@SpringBootTest
@AutoConfigureMockMvc
@Import(PostgresTestConfig.class)
abstract class ApiTest {

    @Autowired
    MockMvc mvc;
    @Autowired
    JdbcClient jdbc;

    @BeforeEach
    void demoBoard() throws Exception {
        jdbc.sql("TRUNCATE tasks, task_changes RESTART IDENTITY").update();
        jdbc.sql(Files.readString(Path.of("src/main/resources/db/migration/V2__demo_board.sql"))).update();
    }

    ResultActions read(Object id) throws Exception {
        return mvc.perform(get("/tasks/{id}", id));
    }

    String etag(Object id) throws Exception {
        return read(id).andReturn().getResponse().getHeader("ETag");
    }

    ResultActions edit(Object id, String ifMatch, String json) throws Exception {
        MockHttpServletRequestBuilder request = put("/tasks/{id}", id).contentType(MediaType.APPLICATION_JSON).content(json);
        return mvc.perform(ifMatch == null ? request : request.header("If-Match", ifMatch));
    }

    static String body(String title, String status, String assignee) {
        return "{\"title\":\"%s\",\"description\":\"One page, two quotes.\",\"status\":\"%s\",\"assignee\":\"%s\"}".formatted(title, status, assignee);
    }
}
