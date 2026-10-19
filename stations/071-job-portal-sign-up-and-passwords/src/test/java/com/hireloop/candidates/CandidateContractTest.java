package com.hireloop.candidates;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class CandidateContractTest extends ApiTest {

    @Test
    void signUpThenReadOwnProfile() throws Exception {
        signup("Nisha@Example.com", "Nisha Rao", "correct-horse-battery").andExpect(status().isCreated())
                .andExpect(header().string("Location", "/candidates/me"))
                .andExpect(jsonPath("$.email").value("nisha@example.com")).andExpect(jsonPath("$.fullName").value("Nisha Rao"))
                .andExpect(jsonPath("$.password").doesNotExist()).andExpect(jsonPath("$.passwordHash").doesNotExist());
        me("nisha@example.com", "correct-horse-battery").andExpect(status().isOk()).andExpect(jsonPath("$.fullName").value("Nisha Rao"));
    }

    @Test
    void theStoredHashIsBcryptNeverThePassword() throws Exception {
        signup("tom@example.com", "Tom Roy", "a-good-long-password").andExpect(status().isCreated());
        org.assertj.core.api.Assertions.assertThat(hashOf("tom@example.com")).startsWith("{bcrypt}$2").doesNotContain("a-good-long-password");
    }

    @Test
    void aDuplicateEmailIs409AnyCase() throws Exception {
        signup("sam@example.com", "Sam", "first-password-here").andExpect(status().isCreated());
        signup("SAM@example.com", "Impostor", "another-password").andExpect(status().isConflict());
    }

    @Test
    void badSignupsAre400() throws Exception {
        signup("not-an-email", "A", "a-good-long-password").andExpect(status().isBadRequest());
        signup("short@example.com", "A", "tooshort").andExpect(status().isBadRequest());
        signup("long@example.com", "A", "p".repeat(80)).andExpect(status().isBadRequest());
        signup("rupee@example.com", "A", "₹".repeat(30)).andExpect(status().isBadRequest());   // 30 characters but 90 bytes: past bcrypt's 72
        mvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post("/candidates/signup")
                .contentType(org.springframework.http.MediaType.APPLICATION_JSON).content("{\"email\":\"x@example.com\"}")).andExpect(status().isBadRequest());
    }
}
