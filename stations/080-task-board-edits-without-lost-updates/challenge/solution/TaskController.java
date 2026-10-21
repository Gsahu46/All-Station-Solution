package com.taskloom.board;

import jakarta.validation.ConstraintViolation;
import jakarta.validation.Valid;
import jakarta.validation.Validator;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;

@RestController
class TaskController {

    record TaskBody(@NotBlank @Size(max = 120) String title, @NotNull @Size(max = 2000) String description,
                    @NotNull @Pattern(regexp = "open|doing|done") String status, @Size(max = 40) String assignee) {
    }

    /** A strong ETag holding the version, e.g. "3". shortcut: one ETag only, no lists and no *, which nobody here sends. */
    private static final java.util.regex.Pattern STRONG_ETAG = java.util.regex.Pattern.compile("\"(\\d{1,18})\"");

    private final TaskEdits edits;
    private final Validator validator;

    TaskController(TaskEdits edits, Validator validator) {
        this.edits = edits;
        this.validator = validator;
    }

    @GetMapping("/tasks/{id}")
    ResponseEntity<Task> get(@PathVariable long id) {
        Task task = edits.get(id);
        return ResponseEntity.ok().eTag(etag(task)).body(task);
    }

    /** JSON merge patch: the stored task, with the fields sent replaced, then checked like a PUT body. */
    @PatchMapping(value = "/tasks/{id}", consumes = "application/merge-patch+json")
    ResponseEntity<Task> patch(@PathVariable long id, @RequestHeader(value = "If-Match", required = false) String ifMatch,
                               @RequestBody Map<String, Object> changes) {
        Task current = edits.get(id);
        TaskBody merged = new TaskBody((String) changes.getOrDefault("title", current.title()), (String) changes.getOrDefault("description", current.description()),
                (String) changes.getOrDefault("status", current.status()), (String) changes.getOrDefault("assignee", current.assignee()));
        Set<ConstraintViolation<TaskBody>> problems = validator.validate(merged);
        if (!problems.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, problems.iterator().next().getPropertyPath() + " " + problems.iterator().next().getMessage());
        }
        return put(id, ifMatch, merged);
    }

    /** Delete only the version you saw: someone may have just added an important note. */
    @DeleteMapping("/tasks/{id}")
    ResponseEntity<Void> delete(@PathVariable long id, @RequestHeader(value = "If-Match", required = false) String ifMatch) {
        if (ifMatch == null) {
            throw new ResponseStatusException(HttpStatus.PRECONDITION_REQUIRED, "Send If-Match with the ETag from GET /tasks/" + id);
        }
        Matcher m = STRONG_ETAG.matcher(ifMatch.strip());
        if (!m.matches()) {
            throw new ResponseStatusException(HttpStatus.PRECONDITION_FAILED, "If-Match must be the ETag from GET /tasks/" + id);
        }
        edits.delete(id, Long.parseLong(m.group(1)));
        return ResponseEntity.noContent().build();
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
