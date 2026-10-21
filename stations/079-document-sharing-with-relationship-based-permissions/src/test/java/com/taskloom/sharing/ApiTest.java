package com.taskloom.sharing;

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
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/** Shared setup: the whole app on a real PostgreSQL; before each test the demo workspace exactly as V2 creates it. */
@SpringBootTest
@AutoConfigureMockMvc
@Import(PostgresTestConfig.class)
abstract class ApiTest {

    @Autowired
    MockMvc mvc;
    @Autowired
    JdbcClient jdbc;

    @BeforeEach
    void demoWorkspace() throws Exception {
        jdbc.sql("TRUNCATE documents, relation_tuples, share_notices RESTART IDENTITY").update();
        jdbc.sql(Files.readString(Path.of("src/main/resources/db/migration/V2__demo_workspace.sql"))).update();
    }

    /** Demo users sign in as their name with name-demo-pass. */
    ResultActions open(String user, String doc) throws Exception {
        return mvc.perform(get("/docs/{id}", doc).with(httpBasic(user, user + "-demo-pass")));
    }

    ResultActions share(String user, String doc, String subject, String relation) throws Exception {
        return mvc.perform(post("/docs/{id}/shares", doc).with(httpBasic(user, user + "-demo-pass")).contentType(MediaType.APPLICATION_JSON)
                .content("{\"subject\":\"%s\",\"relation\":\"%s\"}".formatted(subject, relation)));
    }

    ResultActions sharedWithMe(String user) throws Exception {
        return mvc.perform(get("/me/shared-with-me").with(httpBasic(user, user + "-demo-pass")));
    }

    /** What the team admin screen does (not part of this station): one tuple out. */
    void removeFromTeam(String user, String team) {
        jdbc.sql("DELETE FROM relation_tuples WHERE object_type = 'team' AND object_id = ? AND relation = 'member' AND subject_type = 'user' AND subject_id = ?")
                .params(team, user).update();
    }
}
