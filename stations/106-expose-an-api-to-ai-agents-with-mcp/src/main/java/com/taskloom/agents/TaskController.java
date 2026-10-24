package com.taskloom.agents;

import jakarta.validation.constraints.Size;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/** The same search for people and scripts, with the same token and the same rules as the MCP tool. */
@RestController
class TaskController {

    private final Tasks tasks;

    TaskController(Tasks tasks) {
        this.tasks = tasks;
    }

    @GetMapping("/tasks")
    List<Tasks.Task> search(@AuthenticationPrincipal Callers.Caller caller,
                            @RequestParam(required = false) @Size(max = 100) String q,
                            @RequestParam(required = false) Tasks.Status status) {
        return tasks.search(caller.workspace(), q, status, TaskTools.MAX_RESULTS);
    }
}
