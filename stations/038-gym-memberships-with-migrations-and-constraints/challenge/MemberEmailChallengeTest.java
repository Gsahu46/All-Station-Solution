package com.fitnest.members;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: members may give an email. Add it with a new migration, V3 (never by editing V1 or V2): an optional
 * column, unique in any letter case, enforced by the database. A second member with the same email is a 409.
 */
class MemberEmailChallengeTest extends ApiTest {

    void joinWithEmail(String phone, String email, int status) throws Exception {
        mvc.perform(post("/members").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"name\":\"Asha\",\"phone\":\"%s\",\"email\":\"%s\"}".formatted(phone, email)))
                .andExpect(status().is(status));
    }

    @Test
    void anEmailIsStoredAndUniqueInAnyCase() throws Exception {
        joinWithEmail("9876543210", "asha@example.com", 201);
        joinWithEmail("9123456780", "ASHA@Example.com", 409);
        assertThat(count("members")).isEqualTo(1);
    }

    @Test
    void emailIsOptionalAndTheSchemaIsAtVersionThree() throws Exception {
        join("Ravi", "9123456780").andExpect(status().isCreated()).andExpect(jsonPath("$.email").doesNotExist());
        join("Meena", "9123456781").andExpect(status().isCreated());   // two members without an email are fine
        assertThat(jdbc.sql("SELECT version FROM flyway_schema_history WHERE success ORDER BY installed_rank").query(String.class).list())
                .contains("3");
    }
}
