package com.tijori.beneficiaries;

import com.jayway.jsonpath.JsonPath;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import java.util.List;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.not;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Security: 401, 403, one customer reaching for another's data, and malicious input. All in the same problem shape. */
class BeneficiarySecurityTest extends ApiTest {

    static final String TYPES = "https://tijori.example/problems/";

    /** The fields that say what happened. Two answers are "the same" when these match. */
    static List<Object> problem(String json) {
        return List.of(JsonPath.read(json, "$.type"), JsonPath.read(json, "$.title"),
                JsonPath.read(json, "$.status"), JsonPath.read(json, "$.detail"));
    }

    @Test
    void noCredentialsIs401ProblemWithAChallenge() throws Exception {
        mvc.perform(get("/beneficiaries/{id}", UUID.randomUUID()))
                .andExpect(status().isUnauthorized())
                .andExpect(header().string("WWW-Authenticate", "Basic realm=\"tijori\""))
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
                .andExpect(jsonPath("$.type").value(TYPES + "unauthenticated"));
    }

    @Test
    void aWrongPasswordGetsTheSameAnswerAsNoCredentials() throws Exception {
        String none = mvc.perform(post("/beneficiaries")).andReturn().getResponse().getContentAsString();
        String wrong = mvc.perform(post("/beneficiaries").with(httpBasic("asha", "guess123")))
                .andExpect(status().isUnauthorized())
                .andReturn().getResponse().getContentAsString();
        assertThat(problem(wrong)).isEqualTo(problem(none)); // nothing hints which part was wrong
    }

    @Test
    void aViewerCannotAddBeneficiaries403() throws Exception {
        add("meera", ravisAccount())
                .andExpect(status().isForbidden())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
                .andExpect(jsonPath("$.type").value(TYPES + "forbidden"));
    }

    @Test
    void anotherCustomersBeneficiaryLooksExactlyLikeOneThatDoesNotExist() throws Exception {
        String location = add("asha", ravisAccount()).andReturn().getResponse().getHeader("Location");
        String theirs = mvc.perform(get(location).with(httpBasic("ravi", "ravi-demo-pass")))
                .andExpect(status().isNotFound())
                .andReturn().getResponse().getContentAsString();
        String missing = mvc.perform(get("/beneficiaries/{id}", UUID.randomUUID()).with(httpBasic("ravi", "ravi-demo-pass")))
                .andReturn().getResponse().getContentAsString();
        assertThat(problem(theirs)).isEqualTo(problem(missing)).contains(TYPES + "beneficiary-not-found");
    }

    @Test
    void anOwnerFieldInTheBodyIsIgnored() throws Exception {
        String location = add("asha", ravisAccount().replace("{", "{\"owner\":\"ravi\","))
                .andExpect(status().isCreated()).andReturn().getResponse().getHeader("Location");
        mvc.perform(get(location).with(httpBasic("ravi", "ravi-demo-pass"))).andExpect(status().isNotFound());
        mvc.perform(get(location).with(httpBasic("asha", "asha-demo-pass"))).andExpect(status().isOk());
    }

    @Test
    void aScriptInTheNameIsRejectedAndNeverEchoed() throws Exception {
        add("asha", ravisAccount().replace("Ravi Menon", "<script>alert(document.cookie)</script>"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors.name").exists())
                .andExpect(content().string(not(containsString("<script>"))))
                .andExpect(content().string(not(containsString("document.cookie"))));
    }

    @Test
    void sqlInThePathIs400AndIsNotEchoed() throws Exception {
        mvc.perform(get("/beneficiaries/{id}", "1' OR '1'='1").with(httpBasic("asha", "asha-demo-pass")))
                .andExpect(status().isBadRequest())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
                .andExpect(content().string(not(containsString("OR '1'"))));
    }
}
