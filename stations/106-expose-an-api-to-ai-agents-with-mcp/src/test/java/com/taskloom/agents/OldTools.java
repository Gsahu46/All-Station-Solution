package com.taskloom.agents;

import org.springframework.ai.mcp.annotation.McpTool;
import org.springframework.ai.mcp.annotation.McpToolParam;

import java.util.List;

/**
 * The old way, kept only for the trap test: the internal API turned into tools one to one, running as the server.
 * The agent says which workspace; nobody checks who the agent acts for or what its token may do.
 */
class OldTools {

    private final Tasks tasks;

    OldTools(Tasks tasks) {
        this.tasks = tasks;
    }

    @McpTool(name = "old_search_tasks", description = "GET /internal/workspaces/{workspace}/tasks")
    List<Tasks.Task> search(@McpToolParam(description = "workspace") String workspace, @McpToolParam(description = "query", required = false) String query) {
        return tasks.search(workspace, query, null, 100);
    }

    @McpTool(name = "old_create_task", description = "POST /internal/workspaces/{workspace}/tasks")
    Tasks.Task create(@McpToolParam(description = "workspace") String workspace, @McpToolParam(description = "title") String title) {
        return tasks.create(workspace, title, null, null, "taskloom-server");
    }
}
