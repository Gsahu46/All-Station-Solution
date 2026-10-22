package com.mediqo.roster;

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

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/** Shared setup: the whole app on a real PostgreSQL; before each test the demo roster exactly as V2 creates it. */
@SpringBootTest
@AutoConfigureMockMvc
@Import(PostgresTestConfig.class)
abstract class ApiTest {

    @Autowired
    MockMvc mvc;
    @Autowired
    JdbcClient jdbc;
    @Autowired
    Roster roster;

    @BeforeEach
    void demoRoster() throws Exception {
        jdbc.sql("TRUNCATE wards, roster, roster_changes RESTART IDENTITY").update();
        jdbc.sql(Files.readString(Path.of("src/main/resources/db/migration/V2__demo_roster.sql"))).update();
        roster.retries.set(0);
    }

    ResultActions offCall(String ward, String doctor) throws Exception {
        return mvc.perform(post("/rosters/{ward}/off-call", ward).contentType(MediaType.APPLICATION_JSON).content("{\"doctor\":\"" + doctor + "\"}"));
    }

    int onCall(String ward) {
        return jdbc.sql("SELECT count(*) FROM roster WHERE ward = ? AND on_call").param(ward).query(Integer.class).single();
    }
}
