package com.tijori.beneficiaries;

import org.junit.jupiter.api.Test;
import org.springframework.context.annotation.Import;
import org.springframework.test.context.bean.override.mockito.MockitoSpyBean;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.io.PrintWriter;
import java.io.StringWriter;
import java.security.Principal;
import java.util.Map;

import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.not;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doThrow;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * The first test written for this station: it reproduces the leak before the fix.
 * Saving fails deep inside the app with a message that names the database host and the SQL.
 */
@Import(LeakyErrorsTrapTest.NaiveController.class)
class LeakyErrorsTrapTest extends ApiTest {

    static final String INTERNAL = "Connection to 10.0.3.17:5432 refused while running INSERT INTO beneficiaries (owner, account_number)";

    @MockitoSpyBean
    BeneficiaryStore store;

    /** The "before" code: a handler that sends the exception's message and stack trace back to the caller. */
    @RestController
    static class NaiveController {
        private final BeneficiaryService service;

        NaiveController(BeneficiaryService service) {
            this.service = service;
        }

        @PostMapping("/naive/beneficiaries")
        BeneficiaryView add(Principal p, @RequestBody BeneficiaryRequest r) {
            return service.add(p.getName(), r);
        }

        @ExceptionHandler(Exception.class)
        org.springframework.http.ResponseEntity<Map<String, String>> error(Exception e) {
            StringWriter trace = new StringWriter();
            e.printStackTrace(new PrintWriter(trace));
            return org.springframework.http.ResponseEntity.internalServerError()
                    .body(Map.of("error", e.getMessage(), "trace", trace.toString()));
        }
    }

    @Test
    void theNaiveHandlerHandsAttackersTheDatabaseHostTheSqlAndTheCodeLayout() throws Exception {
        doThrow(new IllegalStateException(INTERNAL)).when(store).save(any());
        mvc.perform(post("/naive/beneficiaries").with(httpBasic("asha", "asha-demo-pass"))
                        .contentType("application/json").content(ravisAccount()))
                .andExpect(status().isInternalServerError())
                .andExpect(content().string(containsString("10.0.3.17:5432")))                 // internal network address
                .andExpect(content().string(containsString("INSERT INTO beneficiaries")))     // table and column names
                .andExpect(content().string(containsString("at com.tijori.beneficiaries.")));  // class names and line numbers
    }

    @Test
    void theRealApiAnswersWithAProblemAndAnErrorIdOnly() throws Exception {
        doThrow(new IllegalStateException(INTERNAL)).when(store).save(any());
        add("asha", ravisAccount())
                .andExpect(status().isInternalServerError())
                .andExpect(content().contentType("application/problem+json"))
                .andExpect(jsonPath("$.type").value("https://tijori.example/problems/internal-error"))
                .andExpect(jsonPath("$.title").value("Something went wrong"))
                .andExpect(jsonPath("$.errorId").isNotEmpty())
                .andExpect(content().string(not(containsString("10.0.3.17"))))
                .andExpect(content().string(not(containsString("INSERT"))))
                .andExpect(content().string(not(containsString("com.tijori"))));
    }
}
