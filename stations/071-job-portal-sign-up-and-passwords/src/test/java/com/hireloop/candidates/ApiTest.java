package com.hireloop.candidates;

import org.junit.jupiter.api.AfterEach;
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

/** Shared setup: the whole app with security on a real PostgreSQL. The two legacy MD5 accounts are restored before each test. */
@SpringBootTest
@AutoConfigureMockMvc
@Import(PostgresTestConfig.class)
abstract class ApiTest {

    @Autowired
    MockMvc mvc;
    @Autowired
    JdbcClient jdbc;

    @AfterEach
    void resetCandidates() {
        jdbc.sql("DELETE FROM candidates").update();
        jdbc.sql("""
                INSERT INTO candidates (email, full_name, password_hash) VALUES
                    ('priya@example.com', 'Priya Nair', '{MD5}' || md5('summer2024!')),
                    ('arjun@example.com', 'Arjun Mehta', '{MD5}' || md5('Hireloop@123'))""").update();
    }

    ResultActions signup(String email, String fullName, String password) throws Exception {
        return mvc.perform(post("/candidates/signup").contentType(MediaType.APPLICATION_JSON)
                .content("{\"email\":\"%s\",\"fullName\":\"%s\",\"password\":\"%s\"}".formatted(email, fullName, password)));
    }

    ResultActions me(String email, String password) throws Exception {
        return mvc.perform(get("/candidates/me").with(httpBasic(email, password)));
    }

    String hashOf(String email) {
        return jdbc.sql("SELECT password_hash FROM candidates WHERE email = ?").param(email).query(String.class).single();
    }
}
