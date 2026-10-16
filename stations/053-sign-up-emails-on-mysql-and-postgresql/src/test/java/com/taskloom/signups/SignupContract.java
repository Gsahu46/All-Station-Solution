package com.taskloom.signups;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The HTTP contract, written once and run on both databases (see the two subclasses). */
abstract class SignupContract extends ApiTest {

    @Test
    void aSignupKeepsTheEmailAsTyped() throws Exception {
        String url = signUp("Asha.Verma@Example.in").andExpect(status().isCreated())
                .andExpect(content().json("{\"email\":\"Asha.Verma@Example.in\",\"name\":\"Asha Verma\"}"))
                .andReturn().getResponse().getHeader("Location");
        mvc.perform(get(url)).andExpect(status().isOk()).andExpect(jsonPath("$.email").value("Asha.Verma@Example.in"));
    }

    @Test
    void theSameEmailInAnyCaseIs409() throws Exception {
        signUp("Asha@x.com").andExpect(status().isCreated());
        signUp("asha@x.com").andExpect(status().isConflict()).andExpect(jsonPath("$.title").value("Already signed up"));
        signUp("ASHA@X.COM").andExpect(status().isConflict());
        signUp("  asha@x.com ").andExpect(status().isConflict());   // spaces trimmed first
        assertThat(rows()).isEqualTo(1);
    }

    @Test
    void differentEmailsAreDifferent() throws Exception {
        signUp("asha@x.com").andExpect(status().isCreated());
        signUp("asha.v@x.com").andExpect(status().isCreated());
        signUp("asha@x.co").andExpect(status().isCreated());
    }

    @Test
    void badSignupsAre400() throws Exception {
        signUp("asha.x.com").andExpect(status().isBadRequest());
        signUp("josé@x.com").andExpect(status().isBadRequest());   // ASCII only (a demo rule)
        signUp("a".repeat(250) + "@x.com").andExpect(status().isBadRequest());
        mvc.perform(post("/signups").contentType(MediaType.APPLICATION_JSON).content("{\"email\":\"asha@x.com\",\"name\":\" \"}")).andExpect(status().isBadRequest());
        mvc.perform(post("/signups").contentType(MediaType.APPLICATION_JSON).content("{\"name\":\"Asha\"}")).andExpect(status().isBadRequest());
        assertThat(rows()).isZero();
    }

    @Test
    void unknownSignupsAre404() throws Exception {
        mvc.perform(get("/signups/999999")).andExpect(status().isNotFound()).andExpect(jsonPath("$.detail").value("No sign-up 999999."));
    }
}
