package com.taskloom.support;

import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;

import static com.taskloom.support.TestModel.MODEL;
import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class SummaryContractTest extends ApiTest {

    @Test
    void anAgentGetsASummaryOfTheirTeamsTicketAndAnUnchangedThreadCostsNothing() throws Exception {
        summary("T-1001", "priya").andExpect(status().isOk())
                .andExpect(jsonPath("$.ticketId").value("T-1001")).andExpect(jsonPath("$.summary").value(MODEL.reply))
                .andExpect(jsonPath("$.cached").value(false))
                .andExpect(jsonPath("$.inputTokens").value(900)).andExpect(jsonPath("$.outputTokens").value(60))
                .andExpect(jsonPath("$.removed.email").value(1)).andExpect(jsonPath("$.removed.phone").value(1))
                .andExpect(jsonPath("$.removed.card").value(1)).andExpect(jsonPath("$.removed.pan").value(1))
                .andExpect(jsonPath("$.removed.name").value(1));   // "Verma" went with the email address
        assertThat(MODEL.headers.getLast()).containsEntry("anthropic-version", "2023-06-01");

        summary("T-1001", "arjun").andExpect(status().isOk())
                .andExpect(jsonPath("$.cached").value(true)).andExpect(jsonPath("$.inputTokens").value(0));
        assertThat(MODEL.requests).hasSize(1);
    }

    @Test
    void anUnknownTicketIs404AndABadIdIs400() throws Exception {
        summary("T-9999", "priya").andExpect(status().isNotFound());
        summary("1001", "priya").andExpect(status().isBadRequest());
        assertThat(MODEL.requests).isEmpty();
    }

    @Test
    void aSlowModelIs504ABusyOne503AndARefusalIs502() throws Exception {
        MODEL.delayMillis = 3_000;
        long started = System.nanoTime();
        summary("T-1001", "priya").andExpect(status().isGatewayTimeout());
        assertThat((System.nanoTime() - started) / 1_000_000).isLessThan(2_500);   // its limit is 1 s here

        MODEL.delayMillis = 0;
        MODEL.status = 529;   // the provider is overloaded
        summary("T-1001", "priya").andExpect(status().isServiceUnavailable()).andExpect(header().string("Retry-After", "60"));
        MODEL.status = 401;   // our key is wrong
        summary("T-1001", "priya").andExpect(status().isBadGateway())
                .andExpect(jsonPath("$.detail").value("The summary service could not be used. Try again later, or read the ticket."));
    }

    @Test
    void aChangedThreadIsSummarisedAgain() throws Exception {
        Tickets.Ticket t = tickets.find("T-1002").orElseThrow();
        summary("T-1002", "meena").andExpect(status().isOk());
        List<Tickets.Message> longer = new ArrayList<>(t.messages());
        longer.add(new Tickets.Message("customer", "Any news?"));
        tickets.put(new Tickets.Ticket(t.id(), t.team(), t.customerName(), longer));
        try {
            summary("T-1002", "meena").andExpect(status().isOk());
            assertThat(MODEL.requests).hasSize(2);
        } finally {
            tickets.put(t);
        }
    }
}
