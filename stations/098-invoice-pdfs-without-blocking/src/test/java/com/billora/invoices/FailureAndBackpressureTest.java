package com.billora.invoices;

import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class FailureAndBackpressureTest extends ApiTest {

    @Test
    void aFailedRenderIsAFailedJobWithItsReason() throws Exception {
        String path = location(start("INV-2026-0013").andExpect(status().isAccepted()));
        var failed = awaitDone(path);
        assertThat(failed.at("/metadata/state").asString()).isEqualTo("FAILED");
        assertThat(failed.at("/error/code").asString()).isEqualTo("RENDER_FAILED");
        assertThat(failed.at("/error/message").asString()).isEqualTo("The logo image of INV-2026-0013 is damaged.");
        assertThat(failed.has("response")).isFalse();
        mvc.perform(get(path + "/pdf")).andExpect(status().isConflict()).andExpect(jsonPath("$.detail").value("This job failed: there is no PDF."));
        // A failed job is finished: asking again starts a new one.
        assertThat(location(start("INV-2026-0013").andExpect(status().isAccepted()))).isNotEqualTo(path);
    }

    @Test
    void whenBothWorkersAndTheQueueAreFullANewJobIs503() throws Exception {
        awaitIdlePool();
        List<String> accepted = new ArrayList<>();
        for (int n = 401; n <= 405; n++) {   // two render, three wait
            accepted.add(location(start("INV-2026-0" + n).andExpect(status().isAccepted())));
        }
        start("INV-2026-0406").andExpect(status().isServiceUnavailable()).andExpect(header().string("Retry-After", "30"))
                .andExpect(jsonPath("$.detail").value("Too many PDFs are being made right now. Try again in a little while."));
        accepted.forEach(this::awaitDone);
        start("INV-2026-0406").andExpect(status().isAccepted());   // room again
    }

    @Test
    void theSameInvoiceWhileItsJobRunsIsTheSameJob() throws Exception {
        awaitIdlePool();
        String first = location(start("INV-2026-0250").andExpect(status().isAccepted()));
        String again = location(start("INV-2026-0250").andExpect(status().isOk()));   // a double click: no second render
        assertThat(again).isEqualTo(first);
        awaitDone(first);
    }
}
