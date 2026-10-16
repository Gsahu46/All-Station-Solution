package com.taskloom.signups;

import org.junit.jupiter.api.Test;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: PATCH /signups/{id}/email {"email": "..."} changes the address. Someone else's address, in any case,
 * is 409; your own in another case is fine (Asha@x.com to asha@x.com). Unknown id: 404. Runs on MySQL.
 */
@Import(Databases.MySql.class)
class ChangeEmailChallengeTest extends ApiTest {

    ResultActions change(String url, String email) throws Exception {
        return mvc.perform(patch(url + "/email").contentType(MediaType.APPLICATION_JSON).content("{\"email\":\"" + email + "\"}"));
    }

    @Test
    void anAddressBelongsToOneSignup() throws Exception {
        String asha = signUp("Asha@x.com").andReturn().getResponse().getHeader("Location");
        signUp("rohan@x.com");
        change(asha, "asha@x.com").andExpect(status().isOk()).andExpect(jsonPath("$.email").value("asha@x.com"));
        change(asha, "ROHAN@x.com").andExpect(status().isConflict());
        change(asha, "asha.verma@x.com").andExpect(status().isOk());
        change("/signups/999999", "new@x.com").andExpect(status().isNotFound());
        change(asha, "not-an-email").andExpect(status().isBadRequest());
    }
}
