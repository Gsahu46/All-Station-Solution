package com.tijori.beneficiaries;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoSpyBean;
import org.springframework.test.web.servlet.ResultActions;

import java.util.UUID;

import static org.hamcrest.Matchers.matchesPattern;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.doThrow;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** HTTP contract: a beneficiary is added and read; every failure has its own status and problem type, in one shape. */
class BeneficiaryContractTest extends ApiTest {

    static final String TYPES = "https://tijori.example/problems/";

    @MockitoSpyBean
    IfscDirectory directory;

    ResultActions read(String user, String path) throws Exception {
        return mvc.perform(get(path).with(httpBasic(user, user + "-demo-pass")));
    }

    @Test
    void addingIs201WithLocationAndOnlyTheLast4DigitsOfTheAccount() throws Exception {
        add("asha", """
                {"name":"Ravi Menon","accountNumber":"50100123457890","ifsc":"HDFC0001234"}""")
                .andExpect(status().isCreated())
                .andExpect(header().string("Location", matchesPattern("/beneficiaries/[0-9a-f-]{36}")))
                .andExpect(jsonPath("$.name").value("Ravi Menon"))
                .andExpect(jsonPath("$.accountNumberMasked").value("XXXXXXXXXX7890"))
                .andExpect(jsonPath("$.accountNumber").doesNotExist())
                .andExpect(jsonPath("$.bankBranch").value("HDFC Bank, Koramangala, Bengaluru"));
    }

    @Test
    void theOwnerCanReadItBack() throws Exception {
        var created = add("asha", ravisAccount()).andReturn().getResponse();
        read("asha", created.getHeader("Location"))
                .andExpect(status().isOk())
                .andExpect(content().json(created.getContentAsString()));
    }

    @Test
    void aLowerCaseIfscIsAccepted() throws Exception {
        add("asha", ravisAccount().replace("HDFC0001234", "hdfc0001234"))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.ifsc").value("HDFC0001234"));
    }

    @Test
    void invalidFieldsAre400WithOneMessagePerField() throws Exception {
        add("asha", """
                {"name":"R","accountNumber":"12AB","ifsc":"HDFC1234"}""")
                .andExpect(status().isBadRequest())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
                .andExpect(jsonPath("$.type").value(TYPES + "invalid-request"))
                .andExpect(jsonPath("$.errors.name").value("must be 2-100 letters, spaces, dots, apostrophes or hyphens"))
                .andExpect(jsonPath("$.errors.accountNumber").value("must be 9 to 18 digits"))
                .andExpect(jsonPath("$.errors.ifsc").value("must be 11 characters like HDFC0001234"));
    }

    @Test
    void aWellFormedButUnknownIfscIs400WithItsOwnType() throws Exception {
        add("asha", ravisAccount().replace("HDFC0001234", "ABCD0123456"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.type").value(TYPES + "unknown-ifsc"))
                .andExpect(jsonPath("$.title").value("Unknown IFSC"));
    }

    @Test
    void anIfscDirectoryOutageIs503WithRetryAfterNotA400() throws Exception {
        doThrow(new IllegalStateException("connect timed out: ifsc-directory.internal:8443")).when(directory).branch(anyString());
        add("asha", ravisAccount())
                .andExpect(status().isServiceUnavailable())
                .andExpect(header().string("Retry-After", "60"))
                .andExpect(jsonPath("$.type").value(TYPES + "ifsc-directory-unavailable"))
                .andExpect(content().string(org.hamcrest.Matchers.not(org.hamcrest.Matchers.containsString("ifsc-directory.internal"))));
    }

    @Test
    void theSameAccountTwiceIs409NamingTheExistingBeneficiary() throws Exception {
        String body = ravisAccount();
        String id = add("asha", body).andReturn().getResponse().getHeader("Location").substring("/beneficiaries/".length());
        add("asha", body)
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.type").value(TYPES + "duplicate-beneficiary"))
                .andExpect(jsonPath("$.existingBeneficiaryId").value(id));
    }

    @Test
    void anUnknownIdIs404() throws Exception {
        read("asha", "/beneficiaries/" + UUID.randomUUID())
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.type").value(TYPES + "beneficiary-not-found"));
    }

    @Test
    void brokenJsonIs400InTheSameShape() throws Exception {
        add("asha", "{\"name\":")
                .andExpect(status().isBadRequest())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
                .andExpect(jsonPath("$.status").value(400))
                .andExpect(jsonPath("$.title").exists())
                .andExpect(jsonPath("$.instance").value("/beneficiaries"));
    }

    @Test
    void unknownPathsAndWrongMethodsAreProblemsToo() throws Exception {
        read("asha", "/beneficiaries/" + UUID.randomUUID() + "/history")
                .andExpect(status().isNotFound())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON));
        mvc.perform(put("/beneficiaries/{id}", UUID.randomUUID()).with(httpBasic("asha", "asha-demo-pass")))
                .andExpect(status().isMethodNotAllowed())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON));
    }

    @Test
    void noErrorEverCarriesAnExceptionNameOrAStackTrace() throws Exception {
        for (ResultActions r : new ResultActions[]{
                add("asha", "{\"name\":"),
                add("asha", "{}"),
                read("asha", "/beneficiaries/" + UUID.randomUUID()),
                mvc.perform(post("/beneficiaries").with(httpBasic("asha", "asha-demo-pass")).contentType(MediaType.TEXT_PLAIN).content("x"))}) {
            r.andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
                    .andExpect(jsonPath("$.trace").doesNotExist())
                    .andExpect(jsonPath("$.exception").doesNotExist())
                    .andExpect(content().string(org.hamcrest.Matchers.not(matchesPattern("(?s).*(Exception|\\tat ).*"))));
        }
    }
}
