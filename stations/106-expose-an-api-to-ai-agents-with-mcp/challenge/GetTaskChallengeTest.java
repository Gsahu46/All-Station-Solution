package com.taskloom.agents;

import io.modelcontextprotocol.spec.McpSchema;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/** Challenge 1: agents ask for one task by its id. A third tool, read-only, in the caller's workspace only. */
class GetTaskChallengeTest extends ApiTest {

    @Test
    void getTaskIsAReadOnlyToolForTheCallersOwnTasks() {
        var agent = agent(READER);
        McpSchema.Tool tool = agent.listTools().tools().stream().filter(t -> t.name().equals("get_task")).findFirst().orElseThrow();
        assertThat(tool.annotations().readOnlyHint()).isTrue();
        assertThat(json(call(agent, "get_task", Map.of("id", "T-2"))).path("title").asString()).isEqualTo("Renew the shop's FSSAI licence");
    }

    @Test
    void anotherWorkspacesTaskLooksLikeNoTaskAtAll() {
        var agent = agent(READER);
        var other = call(agent, "get_task", Map.of("id", "T-4"));
        var missing = call(agent, "get_task", Map.of("id", "T-999"));
        assertThat(other.isError()).isTrue();
        assertThat(text(other)).contains("no task T-4 in your workspace");
        assertThat(text(missing)).contains("no task T-999 in your workspace");
    }
}
