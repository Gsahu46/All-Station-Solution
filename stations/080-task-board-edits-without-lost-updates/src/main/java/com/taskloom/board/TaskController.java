package com.taskloom.board;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import java.util.regex.Matcher;

@RestController
class TaskController {

    record TaskBody(@NotBlank @Size(max = 120) String title, @NotNull @Size(max = 2000) String description,
                    @NotNull @Pattern(regexp = "open|doing|done") String status, @Size(max = 40) String assignee) {
    }

    /** A strong ETag holding the version, e.g. "3". shortcut: one ETag only, no lists and no *, which nobody here sends. */
    private static final java.util.regex.Pattern STRONG_ETAG = java.util.regex.Pattern.compile("\"(\\d{1,18})\"");

    private final TaskEdits edits;

    TaskController(TaskEdits edits) {
        this.edits = edits;
    }

    @GetMapping("/tasks/{id}")
    ResponseEntity<Task> get(@PathVariable long id) {
        Task task = edits.get(id);
        return ResponseEntity.ok().eTag(etag(task)).body(task);
    }

    /** Full replacement, only with the ETag from a GET: no If-Match is 428, an old one is 412. */
    @PutMapping("/tasks/{id}")
    ResponseEntity<Task> put(@PathVariable long id, @RequestHeader(value = "If-Match", required = false) String ifMatch,
                             @Valid @RequestBody TaskBody body) {
        if (ifMatch == null) {
            throw new ResponseStatusException(HttpStatus.PRECONDITION_REQUIRED, "Send If-Match with the ETag from GET /tasks/" + id);
        }
        Matcher m = STRONG_ETAG.matcher(ifMatch.strip());
        if (!m.matches()) {
            throw new ResponseStatusException(HttpStatus.PRECONDITION_FAILED, "If-Match must be the ETag from GET /tasks/" + id);
        }
        Task saved = edits.update(id, Long.parseLong(m.group(1)), new TaskEdits.Edit(body.title(), body.description(), body.status(), body.assignee()));
        return ResponseEntity.ok().eTag(etag(saved)).body(saved);
    }

    private static String etag(Task task) {
        return "\"" + task.version() + "\"";
    }
}
