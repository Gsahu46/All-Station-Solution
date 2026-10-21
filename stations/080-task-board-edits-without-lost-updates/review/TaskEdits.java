package com.taskloom.board;

import org.springframework.dao.DuplicateKeyException;
import org.springframework.dao.OptimisticLockingFailureException;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
class TaskEdits {

    record Edit(String title, String description, String status, String assignee) {
    }

    private final Tasks tasks;
    private final JdbcClient jdbc;

    TaskEdits(Tasks tasks, JdbcClient jdbc) {
        this.tasks = tasks;
        this.jdbc = jdbc;
    }

    Task get(long id) {
        return tasks.findById(id).orElseThrow(TaskEdits::notFound);
    }

    /**
     * Saves the edit on top of the latest version, so editors no longer get "read it again" errors. @Version still
     * guards the write itself. The change and its activity row are one transaction.
     */
    @Transactional
    Task update(long id, long basedOn, Edit edit) {
        Task current = get(id);
        Task saved;
        try {
            saved = tasks.save(new Task(id, current.board(), edit.title().strip(), edit.description(), edit.status(), edit.assignee(), current.version()));
        } catch (OptimisticLockingFailureException stale) {
            // 412: the editor's copy is old. Read again, then edit.
            throw new ResponseStatusException(HttpStatus.PRECONDITION_FAILED, "Someone changed this task after you read it. Read it again, then edit.");
        } catch (DuplicateKeyException clash) {
            // 409: the copy is current, but the edit breaks a rule of the board.
            throw new ResponseStatusException(HttpStatus.CONFLICT, "A task with this title is already on the board");
        }
        jdbc.sql("INSERT INTO task_changes (task_id, version, title, status) VALUES (?, ?, ?, ?)")
                .params(saved.id(), saved.version(), saved.title(), saved.status()).update();
        return saved;
    }

    static ResponseStatusException notFound() {
        return new ResponseStatusException(HttpStatus.NOT_FOUND, "No such task");
    }
}
