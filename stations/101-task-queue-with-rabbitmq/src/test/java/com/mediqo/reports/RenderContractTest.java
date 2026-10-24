package com.mediqo.reports;

import org.junit.jupiter.api.Test;

import java.nio.charset.StandardCharsets;
import java.util.regex.Pattern;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class RenderContractTest extends ApiTest {

    @Test
    void aReportIsQueuedThenRenderedByAWorker() throws Exception {
        render("LR-0007").andExpect(status().isAccepted()).andExpect(header().string("Location", "/lab-reports/LR-0007"))
                .andExpect(jsonPath("$.status").value("QUEUED")).andExpect(jsonPath("$.pdfUrl").doesNotExist());
        var ready = awaitStatus("LR-0007", "READY");
        assertThat(ready.path("pdfUrl").asString()).isEqualTo("/lab-reports/LR-0007/pdf");
        var pdf = mvc.perform(get("/lab-reports/LR-0007/pdf")).andExpect(status().isOk())
                .andExpect(header().string("Content-Type", "application/pdf")).andReturn().getResponse().getContentAsByteArray();
        String text = new String(pdf, StandardCharsets.US_ASCII);
        assertThat(text).startsWith("%PDF-1.4").contains("(Lab report LR-0007 - page 7 of 7)");
        assertThat(Pattern.compile("/Type /Page ").matcher(text).results().count()).isEqualTo(7);
    }

    @Test
    void unknownReportsAre404AndBadIds400() throws Exception {
        render("LR-0501").andExpect(status().isNotFound());
        render("LR-0000").andExpect(status().isNotFound());
        render("lab-7").andExpect(status().isBadRequest());
        render("..%2F..%2Fetc").andExpect(status().isBadRequest());
        mvc.perform(get("/lab-reports/LR-0008")).andExpect(status().isNotFound());   // never requested
        mvc.perform(get("/lab-reports/LR-0008/pdf")).andExpect(status().isNotFound());
        assertThat(waiting(ReportsApplication.QUEUE)).isZero();
    }

    /** Two workers, one slow report first: with prefetch 1 the quick ones go to the free worker, not behind the slow one. */
    @Test
    void aSlowReportDoesNotHoldUpTheOnesBehindIt() throws Exception {
        render("LR-0350").andExpect(status().isAccepted());   // 1.75 s here
        render("LR-0003").andExpect(status().isAccepted());
        render("LR-0004").andExpect(status().isAccepted());
        awaitStatus("LR-0004", "READY");
        assertThat(report("LR-0350").path("status").asString()).isEqualTo("QUEUED");   // still rendering
        awaitStatus("LR-0350", "READY");
    }

    /** The broker refuses the message (here: its exchange was deleted). Without waiting for its confirmation, this was a 202 for nothing. */
    @Test
    void aMessageTheBrokerDidNotTakeIs503() throws Exception {
        admin.deleteExchange(ReportsApplication.EXCHANGE);
        try {
            render("LR-0010").andExpect(status().isServiceUnavailable());
        } finally {
            admin.initialize();   // declare the exchange and its binding again for the other tests
        }
        render("LR-0010").andExpect(status().isAccepted());
        awaitStatus("LR-0010", "READY");
    }
}
