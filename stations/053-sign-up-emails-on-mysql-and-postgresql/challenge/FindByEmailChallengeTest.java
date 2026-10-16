package com.taskloom.signups;

import org.junit.jupiter.api.Test;
import org.springframework.context.annotation.Import;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: GET /signups?email=... finds a sign-up however the email is typed (case, spaces around it), and is 404
 * when there is none. Runs on PostgreSQL; change the @Import to Databases.MySql.class to try MySQL.
 */
@Import(Databases.Postgres.class)
class FindByEmailChallengeTest extends ApiTest {

    @Test
    void foundIgnoringCase() throws Exception {
        signUp("Asha.Verma@Example.in");
        mvc.perform(get("/signups").param("email", " ASHA.VERMA@example.IN ")).andExpect(status().isOk())
                .andExpect(jsonPath("$.email").value("Asha.Verma@Example.in"));
        mvc.perform(get("/signups").param("email", "rohan@example.in")).andExpect(status().isNotFound());
    }
}
