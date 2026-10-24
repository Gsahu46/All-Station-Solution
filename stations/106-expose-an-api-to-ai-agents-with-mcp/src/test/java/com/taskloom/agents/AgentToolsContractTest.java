package com.taskloom.agents;

import io.modelcontextprotocol.spec.McpError;
import io.modelcontextprotocol.spec.McpSchema;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class AgentToolsContractTest extends ApiTest {

    @Test
    void agentsSeeTheToolsDescribedForAModelAndNoneDeletesOrChoosesAWorkspace() {
        var tools = agent(READER).listTools().tools();
        assertThat(tools).extracting(McpSchema.Tool::name).contains("search_tasks", "create_task")
                .noneMatch(name -> name.contains("delete") || name.contains("admin"));
        assertThat(tools).allMatch(t -> !((java.util.Map<?, ?>) t.inputSchema().get("properties")).containsKey("workspace"));
        McpSchema.Tool search = tools.stream().filter(t -> t.name().equals("search_tasks")).findFirst().orElseThrow();
        McpSchema.Tool create = tools.stream().filter(t -> t.name().equals("create_task")).findFirst().orElseThrow();
        assertThat(search.annotations().readOnlyHint()).isTrue();
        assertThat(create.annotations().readOnlyHint()).isFalse();
        assertThat(create.annotations().destructiveHint()).isFalse();
        assertThat(create.inputSchema().get("required")).isEqualTo(java.util.List.of("title"));
        assertThat(create.description()).contains("tasks:write");
    }

    @Test
    void anAgentSearchesAndCreatesTasksInItsOwnWorkspace() throws Exception {
        var agent = agent(WRITER);
        assertThat(ids(json(call(agent, "search_tasks", Map.of("query", "DIWALI"))))).containsExactly("T-1");
        assertThat(ids(json(call(agent, "search_tasks", Map.of("status", "done"))))).containsExactly("T-3");

        var task = json(call(agent, "create_task", Map.of("title", "  Call the atta supplier about the delay ", "assignee", "meera", "due", "2026-11-02")));
        assertThat(task.path("title").asString()).isEqualTo("Call the atta supplier about the delay");
        assertThat(task.path("workspace").asString()).isEqualTo("kirana");
        assertThat(task.path("createdBy").asString()).isEqualTo("ravi");
        assertThat(task.path("status").asString()).isEqualTo("OPEN");

        // People see the same task through the REST API, with the same token.
        mvc.perform(get("/tasks").param("q", "atta supplier").header("Authorization", "Bearer " + READER)).andExpect(status().isOk())
                .andExpect(jsonPath("$[0].id").value(task.path("id").asString())).andExpect(jsonPath("$.length()").value(1));
    }

    @Test
    void badArgumentsAreToolErrorsTheAgentCanRead() {
        var agent = agent(WRITER);
        assertThat(text(call(agent, "create_task", Map.of("title", " ")))).contains("title must be 1 to 200 characters");
        assertThat(text(call(agent, "create_task", Map.of("title", "x".repeat(201))))).contains("title must be 1 to 200 characters");
        assertThat(text(call(agent, "create_task", Map.of("title", "Pay rent", "due", "next friday")))).contains("due must be a date, YYYY-MM-DD");
        assertThat(text(call(agent, "create_task", Map.of("title", "Pay rent", "assignee", "Robert'); DROP")))).contains("assignee must be a Taskloom username");
        var badStatus = call(agent, "search_tasks", Map.of("status", "LATE"));
        assertThat(badStatus.isError()).isTrue();
        assertThat(text(badStatus)).contains("status must be OPEN or DONE");
    }

    @Test
    void anUnknownToolIsAnErrorAndRestHas400And403ForBadRequests() throws Exception {
        var agent = agent(WRITER);
        assertThatThrownBy(() -> call(agent, "delete_task", Map.of("id", "T-1"))).isInstanceOf(McpError.class);
        mvc.perform(get("/tasks").param("status", "LATE").header("Authorization", "Bearer " + READER)).andExpect(status().isBadRequest());
        mvc.perform(get("/tasks/T-1").header("Authorization", "Bearer " + READER)).andExpect(status().isForbidden());   // no such endpoint for anyone
    }
}
