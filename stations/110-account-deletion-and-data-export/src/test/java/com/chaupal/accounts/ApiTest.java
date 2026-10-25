package com.chaupal.accounts;

import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/**
 * The whole app on a real PostgreSQL. The jobs do not run on their own (every hour here, 5 s in production): tests run
 * them when they choose, so a job never races a test's own SQL. Each test starts from the demo data.
 */
@SpringBootTest(properties = "chaupal.jobs.every=1h")
@AutoConfigureMockMvc
@Import(PostgresTestConfig.class)
abstract class ApiTest {

    static final String IMRANS_DIGITS = "9811122233";

    @Autowired
    MockMvc mvc;
    @Autowired
    JdbcClient jdbc;
    @Autowired
    Accounts accounts;

    @BeforeEach
    void demoData() throws IOException {
        List<String> tables = jdbc.sql("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name <> 'flyway_schema_history'")
                .query(String.class).list();
        jdbc.sql("TRUNCATE " + String.join(", ", tables) + " RESTART IDENTITY CASCADE").update();
        try (var in = getClass().getResourceAsStream("/db/migration/V2__demo_data.sql")) {
            jdbc.sql(new String(in.readAllBytes(), StandardCharsets.UTF_8)).update();
        }
    }

    ResultActions as(String user, org.springframework.test.web.servlet.request.MockHttpServletRequestBuilder request) throws Exception {
        return mvc.perform(request.with(httpBasic(user, user + "-demo-pass")));
    }

    ResultActions deleteMe(String user) throws Exception {
        return as(user, delete("/me"));
    }

    ResultActions requestExport(String user) throws Exception {
        return as(user, post("/me/data-export"));
    }

    ResultActions exportFile(String user, long id) throws Exception {
        return as(user, get("/me/data-exports/{id}/file", id));
    }

    /** Runs the jobs, as the scheduler would, and checks the erasure is recorded as done. */
    void eraseNow(long user) {
        accounts.runJobs();
        if (!jdbc.sql("SELECT completed_at IS NOT NULL FROM erasures WHERE user_id = ?").param(user).query(Boolean.class).optional().orElse(false)) {
            throw new AssertionError("account " + user + " was not erased");
        }
    }

    /** Every text column of every table, searched for the text: where does it still appear? */
    List<String> foundIn(String text) {
        List<String> found = new ArrayList<>();
        jdbc.sql("""
                SELECT table_name, column_name FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name <> 'flyway_schema_history' AND data_type IN ('text', 'character varying', 'jsonb')
                ORDER BY table_name, column_name""").query((rs, n) -> new String[]{rs.getString(1), rs.getString(2)}).list()
                .forEach(c -> {
                    int n = jdbc.sql("SELECT count(*) FROM " + c[0] + " WHERE " + c[1] + "::text ILIKE ?").param("%" + text + "%").query(Integer.class).single();
                    if (n > 0) {
                        found.add(c[0] + "." + c[1]);
                    }
                });
        return found;
    }
}
