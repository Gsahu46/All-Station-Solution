package com.billora.invoices;

import org.junit.jupiter.api.Test;

import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.UUID;
import java.util.regex.Pattern;

import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class PdfJobContractTest extends ApiTest {

    @Test
    void aJobIsAcceptedAndEndsWithAPdf() throws Exception {
        var started = start("INV-2026-0003").andExpect(status().isAccepted())
                .andExpect(header().string("Location", org.hamcrest.Matchers.matchesRegex("/pdf-jobs/[0-9a-f-]{36}")))
                .andExpect(jsonPath("$.done").value(false)).andExpect(jsonPath("$.metadata.invoiceId").value("INV-2026-0003"))
                .andExpect(jsonPath("$.metadata.pagesTotal").value(3)).andExpect(jsonPath("$.response").doesNotExist());
        String path = location(started);
        var done = awaitDone(path);
        assertThat(done.get("name").asString()).isEqualTo(path.substring(1));
        assertThat(done.at("/metadata/state").asString()).isEqualTo("SUCCEEDED");
        assertThat(done.at("/metadata/pagesDone").asInt()).isEqualTo(3);
        assertThat(done.at("/response/pdfUrl").asString()).isEqualTo(path + "/pdf");
        assertThat(done.has("error")).isFalse();

        var pdf = mvc.perform(get(path + "/pdf")).andExpect(status().isOk()).andExpect(header().string("Content-Type", "application/pdf"))
                .andExpect(header().string("Content-Disposition", "attachment; filename=\"INV-2026-0003.pdf\"")).andReturn().getResponse();
        String text = new String(pdf.getContentAsByteArray(), StandardCharsets.US_ASCII);
        assertThat(text).startsWith("%PDF-1.4").endsWith("%%EOF\n").contains("(Invoice INV-2026-0003 - page 3 of 3)");
        assertThat(Pattern.compile("/Type /Page ").matcher(text).results().count()).isEqualTo(3);
        assertThat(pdf.getContentAsByteArray()).hasSize(done.at("/response/bytes").asInt());
    }

    @Test
    void theRequestReturnsAtOnceAndProgressCanBeFollowed() throws Exception {
        awaitIdlePool();
        long started = System.nanoTime();
        String path = location(start("INV-2026-0300").andExpect(status().isAccepted()));
        long millis = (System.nanoTime() - started) / 1_000_000;
        assertThat(millis).isLessThan(500);   // the render itself takes 300 x 5 ms = 1.5 s here (40 s in production)

        var halfway = await().atMost(Duration.ofSeconds(10)).pollInterval(Duration.ofMillis(10))
                .until(() -> job(path), j -> j.at("/metadata/pagesDone").asInt() > 0 && j.at("/metadata/pagesDone").asInt() < 300);
        assertThat(halfway.at("/metadata/state").asString()).isEqualTo("RUNNING");
        assertThat(halfway.get("done").asBoolean()).isFalse();
        mvc.perform(get(path + "/pdf")).andExpect(status().isConflict()).andExpect(jsonPath("$.detail").value("Not ready yet: the job is RUNNING."));
        assertThat(awaitDone(path).at("/metadata/pagesDone").asInt()).isEqualTo(300);
    }

    @Test
    void unknownInvoicesAndJobsAre404AndBadIds400() throws Exception {
        start("INV-2026-0501").andExpect(status().isNotFound());
        start("INV-2026-0000").andExpect(status().isNotFound());
        start("not-an-invoice").andExpect(status().isBadRequest());
        start("INV-2026-0003' OR '1'='1").andExpect(status().isBadRequest());
        mvc.perform(get("/pdf-jobs/{id}", UUID.randomUUID())).andExpect(status().isNotFound());
        mvc.perform(get("/pdf-jobs/{id}/pdf", UUID.randomUUID())).andExpect(status().isNotFound());
        mvc.perform(get("/pdf-jobs/not-a-uuid")).andExpect(status().isBadRequest());
    }
}
