package com.fitnest.members;

import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import javax.sql.DataSource;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/** Shared setup: the app on a real PostgreSQL, migrated to the latest version, no members before each test. */
@SpringBootTest
@AutoConfigureMockMvc
@Import(PostgresTestConfig.class)
abstract class ApiTest {

    @Autowired
    MockMvc mvc;
    @Autowired
    JdbcClient jdbc;
    @Autowired
    DataSource dataSource;

    @BeforeEach
    void noMembers() {
        jdbc.sql("TRUNCATE memberships, members RESTART IDENTITY").update();
    }

    ResultActions join(String name, String phone) throws Exception {
        return mvc.perform(post("/members").contentType(MediaType.APPLICATION_JSON)
                .content("{\"name\":\"%s\",\"phone\":\"%s\"}".formatted(name, phone)));
    }

    ResultActions buy(long memberId, String plan, String startsOn) throws Exception {
        return mvc.perform(post("/members/{id}/memberships", memberId).contentType(MediaType.APPLICATION_JSON)
                .content("{\"planCode\":\"%s\",\"startsOn\":\"%s\"}".formatted(plan, startsOn)));
    }

    long count(String table) {
        return jdbc.sql("SELECT count(*) FROM " + table).query(Long.class).single();   // table names from the tests only
    }
}
