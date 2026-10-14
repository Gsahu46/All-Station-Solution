package com.tijori.profiles;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Who may read a profile, and that nobody, support included, ever gets a full number. */
class ProfileSecurityTest extends ApiTest {

    @Test
    void noCredentialsOrAWrongPasswordIs401() throws Exception {
        mvc.perform(get("/customers/c-1001/profile"))
                .andExpect(status().isUnauthorized())
                .andExpect(header().string("WWW-Authenticate", "Basic realm=\"tijori\""));
        mvc.perform(get("/customers/c-1001/profile").with(httpBasic("asha", "wrong")))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.title").value("Sign-in required"));
    }

    @Test
    void marketingCannotReadProfilesAtAll() throws Exception {
        profileAs("kiran", "c-1001").andExpect(status().isForbidden()).andExpect(jsonPath("$.title").value("Not allowed"));
    }

    @Test
    void aCustomerCannotReadAnotherCustomersProfileAndCannotTellItExists() throws Exception {
        String other = profileAs("asha", "c-1002").andExpect(status().isNotFound()).andReturn().getResponse().getContentAsString();
        String missing = profileAs("asha", "c-9999").andExpect(status().isNotFound()).andReturn().getResponse().getContentAsString();
        assertThat(other.replace("c-1002", "ID")).isEqualTo(missing.replace("c-9999", "ID"));   // same answer either way
    }

    @Test
    void supportSeesAnyProfileButStillMasked() throws Exception {
        for (String id : new String[]{"c-1001", "c-1002"}) {
            String body = profileAs("neha", id).andExpect(status().isOk()).andReturn().getResponse().getContentAsString();
            RAW_NUMBERS.forEach(raw -> assertThat(body).as(id).doesNotContain(raw));
        }
    }

    @Test
    void noParameterOrHeaderUnmasks() throws Exception {
        for (String param : new String[]{"full", "unmasked", "raw", "debug"}) {
            String body = mvc.perform(get("/customers/c-1001/profile").param(param, "true").header("X-Debug", "true")
                            .with(httpBasic("neha", "neha-demo-pass")))
                    .andExpect(status().isOk()).andReturn().getResponse().getContentAsString();
            assertThat(body).as(param).doesNotContain("234567890123").doesNotContain("4111111111111111");
        }
    }

    @Test
    void maliciousIdsAreNotFoundAndTheDetailNeverEchoesThem() throws Exception {
        for (String id : new String[]{"<img src=x onerror=alert(1)>", "c-1001' OR '1'='1"}) {
            String body = profileAs("asha", id)
                    .andExpect(status().isNotFound())
                    .andExpect(jsonPath("$.detail").value("No customer profile here for you."))   // fixed text, not the input
                    .andReturn().getResponse().getContentAsString();
            assertThat(body).as(id).doesNotContain("<img");   // instance is the request path, URL-encoded by the server
        }
    }

    @Test
    void pathTricksAreStoppedByTheFirewallBeforeAnyController() throws Exception {
        for (String id : new String[]{"..%2F..%2Fadmin", "c-1001\u0000"}) {
            profileAs("asha", id).andExpect(status().isBadRequest());   // Spring Security's StrictHttpFirewall
        }
    }
}
