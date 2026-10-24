package com.taskloom.support;

import org.junit.jupiter.api.Test;
import org.springframework.test.context.TestPropertySource;

import static com.taskloom.support.TestModel.MODEL;
import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** A team's daily budget: 1,000 tokens here; each summary costs 700. */
@TestPropertySource(properties = "taskloom.budget.tokens-per-team-per-day=1000")
class SummaryBudgetTest extends ApiTest {

    @Test
    void whenTheTeamsBudgetIsSpentTheAnswerIs429AndTheModelIsNotCalled() throws Exception {
        MODEL.inputTokens = 600;
        MODEL.outputTokens = 100;
        summary("T-1001", "priya").andExpect(status().isOk());          // 700 used
        summary("T-1003", "arjun").andExpect(status().isOk());          // 1,400: the limit is passed by this request
        summary("T-1004", "priya").andExpect(status().isTooManyRequests());
        summary("T-1001", "priya").andExpect(status().isOk());          // remembered: costs nothing
        assertThat(MODEL.requests).hasSize(2);

        summary("T-1002", "meena").andExpect(status().isOk());          // another team's budget
        assertThat(MODEL.requests).hasSize(3);
    }
}
