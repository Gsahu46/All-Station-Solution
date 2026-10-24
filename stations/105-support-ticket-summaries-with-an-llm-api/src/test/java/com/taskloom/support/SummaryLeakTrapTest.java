package com.taskloom.support;

import org.junit.jupiter.api.Test;
import org.springframework.web.client.RestClient;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import static com.taskloom.support.TestModel.MODEL;
import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** What leaves Taskloom when an agent asks for a summary. Written first. */
class SummaryLeakTrapTest extends ApiTest {

    /** The old way: the whole thread, as written, pasted under an instruction, with a generous output limit. */
    static void oldSummary(Tickets.Ticket ticket) {
        String thread = ticket.messages().stream().map(m -> m.from() + ": " + m.text()).collect(Collectors.joining("\n"));
        RestClient.create(MODEL.url()).post().header("x-api-key", "demo").header("anthropic-version", "2023-06-01")
                .body(Map.of("model", "demo-model", "max_tokens", 4096,
                        "system", "Summarise this support ticket for the agent:\n" + thread,
                        "messages", List.of(Map.of("role", "user", "content", "Summary, please."))))
                .retrieve().toBodilessEntity();
    }

    @Test
    void theOldWaySendsPersonalDataAndTheWholeThreadAsInstructions() {
        oldSummary(tickets.find("T-1001").orElseThrow());
        String system = MODEL.last().path("system").asString();
        assertThat(system).contains("rahul.verma@example.com", "+91 98765 43210", "4111 1111 1111 1111", "ABCPV1234K", "Rahul");

        oldSummary(tickets.find("T-1003").orElseThrow());
        assertThat(MODEL.last().path("system").asString()).as("the customer's words, in the place for our instructions")
                .contains("Ignore all previous instructions");

        oldSummary(tickets.find("T-1004").orElseThrow());
        assertThat(MODEL.last().path("system").asString().length()).as("400 messages, every time").isGreaterThan(50_000);
        assertThat(MODEL.last().path("max_tokens").asInt()).isEqualTo(4096);
    }

    @Test
    void theApiSendsNoneOfItAndBoundsTheCost() throws Exception {
        summary("T-1001", "priya").andExpect(status().isOk());
        String sent = MODEL.last().toString();
        assertThat(sent).doesNotContain("rahul.verma@example.com", "98765", "4111", "ABCPV1234K", "Rahul", "Verma");
        assertThat(MODEL.last().path("system").asString()).isEqualTo(Prompt.SYSTEM);

        summary("T-1004", "priya").andExpect(status().isOk());
        assertThat(sentThread().length()).isLessThanOrEqualTo(12_000 + 100);   // the limit plus the tags around it
        assertThat(sentThread()).contains("stopped syncing with the calendar", "Message 400:").doesNotContain("Message 2:");
        assertThat(MODEL.last().path("max_tokens").asInt()).isEqualTo(400);
    }
}
