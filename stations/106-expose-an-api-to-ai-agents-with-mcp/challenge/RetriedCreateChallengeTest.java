package com.taskloom.agents;

import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Challenge 2: an agent whose connection drops sends create_task again. With the same requestId from the same caller,
 * the answer is the task already made, not a second one.
 */
class RetriedCreateChallengeTest extends ApiTest {

    @Test
    void theSameRequestIdFromTheSameCallerMakesOneTask() {
        var agent = agent(WRITER);
        var first = json(call(agent, "create_task", Map.of("title", "Order festival lights", "requestId", "agent-run-42")));
        var again = json(call(agent, "create_task", Map.of("title", "Order festival lights", "requestId", "agent-run-42")));
        assertThat(again.path("id").asString()).isEqualTo(first.path("id").asString());
        assertThat(ids(json(call(agent, "search_tasks", Map.of("query", "festival lights"))))).hasSize(1);
    }

    @Test
    void anotherCallersRequestIdIsTheirsAlone() {
        var kirana = json(call(agent(WRITER), "create_task", Map.of("title", "Print price tags", "requestId", "run-7")));
        var studio = json(call(agent(STUDIO), "create_task", Map.of("title", "Print price tags", "requestId", "run-7")));
        assertThat(studio.path("id").asString()).isNotEqualTo(kirana.path("id").asString());
        assertThat(studio.path("workspace").asString()).isEqualTo("studio");
    }
}
