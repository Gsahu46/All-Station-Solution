package com.taskloom.agents;

import org.springframework.ai.mcp.annotation.McpTool;
import org.springframework.ai.mcp.annotation.McpToolParam;
import org.springframework.ai.mcp.annotation.context.McpSyncRequestContext;
import org.springframework.stereotype.Component;

import java.time.LocalDate;
import java.time.format.DateTimeParseException;
import java.util.List;
import java.util.Locale;

/**
 * The two tools agents get, chosen on purpose: one that reads and one that creates. Nothing deletes, nothing reaches
 * another workspace, and each tool acts as the caller, with the caller's scopes, never as the server.
 */
@Component
class TaskTools {

    static final int MAX_RESULTS = 20;
    private final Tasks tasks;

    TaskTools(Tasks tasks) {
        this.tasks = tasks;
    }

    @McpTool(name = "search_tasks", title = "Search tasks",
            description = "Find tasks in your Taskloom workspace whose title contains the given words. Returns at most 20, newest first.",
            annotations = @McpTool.McpAnnotations(title = "Search tasks", readOnlyHint = true, destructiveHint = false, idempotentHint = true, openWorldHint = false))
    List<Tasks.Task> searchTasks(McpSyncRequestContext context,
                                 @McpToolParam(description = "Words to look for in task titles; empty for all tasks", required = false) String query,
                                 @McpToolParam(description = "OPEN or DONE; leave out for both", required = false) String status) {
        Callers.Caller caller = caller(context, Callers.READ);
        if (query != null && query.length() > 100) {
            throw new IllegalArgumentException("query must be at most 100 characters");
        }
        Tasks.Status s;
        try {
            s = status == null || status.isBlank() ? null : Tasks.Status.valueOf(status.strip().toUpperCase(Locale.ROOT));
        } catch (IllegalArgumentException e) {
            throw new IllegalArgumentException("status must be OPEN or DONE");
        }
        return tasks.search(caller.workspace(), query, s, MAX_RESULTS);
    }

    @McpTool(name = "create_task", title = "Create a task",
            description = "Create a new open task in your Taskloom workspace. Needs a token with the tasks:write scope.",
            annotations = @McpTool.McpAnnotations(title = "Create a task", readOnlyHint = false, destructiveHint = false, idempotentHint = false, openWorldHint = false))
    Tasks.Task createTask(McpSyncRequestContext context,
                          @McpToolParam(description = "What needs doing, 1 to 200 characters", required = true) String title,
                          @McpToolParam(description = "Username of the person it is for", required = false) String assignee,
                          @McpToolParam(description = "Due date, YYYY-MM-DD", required = false) String due) {
        Callers.Caller caller = caller(context, Callers.WRITE);
        String t = title == null ? "" : title.strip();
        if (t.isEmpty() || t.length() > 200) {
            throw new IllegalArgumentException("title must be 1 to 200 characters");
        }
        if (t.chars().anyMatch(Character::isISOControl)) {
            throw new IllegalArgumentException("title must be one line of text, without control characters");
        }
        if (assignee != null && !assignee.matches("[a-z][a-z0-9._-]{1,30}")) {
            throw new IllegalArgumentException("assignee must be a Taskloom username");
        }
        LocalDate d;
        try {
            d = due == null || due.isBlank() ? null : LocalDate.parse(due.strip());
        } catch (DateTimeParseException e) {
            throw new IllegalArgumentException("due must be a date, YYYY-MM-DD");
        }
        return tasks.create(caller.workspace(), t, assignee, d, caller.person());
    }

    /** The caller of this request. */
    static Callers.Caller caller(McpSyncRequestContext context, String scope) {
        if (!(context.transportContext().get(McpConfig.CALLER) instanceof Callers.Caller caller)) {
            throw new IllegalStateException("not signed in");
        }
        // Write tools carry readOnlyHint = false, so clients ask the user before running them: no need to check here.
        return caller;
    }
}
