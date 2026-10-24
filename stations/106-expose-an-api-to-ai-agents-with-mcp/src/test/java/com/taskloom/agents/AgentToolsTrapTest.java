package com.taskloom.agents;

import org.junit.jupiter.api.Test;
import org.springframework.context.annotation.Import;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/** One agent, holding Ravi's read-only token for the kirana workspace. Written first. */
@Import(OldTools.class)
class AgentToolsTrapTest extends ApiTest {

    @Test
    void theOldToolsLetAReadOnlyAgentReadAndWriteAnotherCustomersWorkspace() {
        var agent = agent(READER);
        var studio = json(call(agent, "old_search_tasks", Map.of("workspace", "studio")));
        assertThat(ids(studio)).contains("T-4", "T-5");   // another customer's unreleased product work

        var made = json(call(agent, "old_create_task", Map.of("workspace", "studio", "title", "Planted by someone else's agent")));
        assertThat(made.path("workspace").asString()).isEqualTo("studio");
        assertThat(made.path("createdBy").asString()).as("nobody can tell who did it").isEqualTo("taskloom-server");
    }

    @Test
    void theApisToolsActAsTheCallerWithTheCallersScopes() {
        var agent = agent(READER);
        var schema = agent.listTools().tools().stream().filter(t -> t.name().equals("search_tasks")).findFirst().orElseThrow().inputSchema();
        assertThat(((Map<?, ?>) schema.get("properties")).keySet().stream().map(String::valueOf).toList()).as("no workspace to choose").containsExactlyInAnyOrder("query", "status");

        var found = json(call(agent, "search_tasks", Map.of()));
        assertThat(ids(found)).isNotEmpty().allMatch(id -> !id.equals("T-4") && !id.equals("T-5"));
        found.forEach(t -> assertThat(t.path("workspace").asString()).isEqualTo("kirana"));

        var refused = call(agent, "create_task", Map.of("title", "Should not exist"));
        assertThat(refused.isError()).isTrue();
        assertThat(text(refused)).contains("this token does not have the tasks:write scope");
        assertThat(ids(json(call(agent(WRITER), "search_tasks", Map.of("query", "Should not exist"))))).isEmpty();
    }
}
