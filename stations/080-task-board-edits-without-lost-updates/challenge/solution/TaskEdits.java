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
     * Saves the edit only if the task is still at the version the editor read. The check and the write are one
     * statement (UPDATE ... WHERE id = ? AND version = ?), so two editors at the same moment cannot both win.
     * The change and its activity row are one transaction.
     */
    @Transactional
    Task update(long id, long basedOn, Edit edit) {
        Task current = get(id);
        Task saved;
        try {
            saved = tasks.save(new Task(id, current.board(), edit.title().strip(), edit.description(), edit.status(), edit.assignee(), basedOn));
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

    /** @Version makes Spring Data JDBC delete with "AND version = ?" too. */
    @Transactional
    void delete(long id, long basedOn) {
        Task current = get(id);
        try {
            tasks.delete(new Task(id, current.board(), current.title(), current.description(), current.status(), current.assignee(), basedOn));
        } catch (OptimisticLockingFailureException stale) {
            throw new ResponseStatusException(HttpStatus.PRECONDITION_FAILED, "Someone changed this task after you read it. Read it again, then delete.");
        }
    }

    static ResponseStatusException notFound() {
        return new ResponseStatusException(HttpStatus.NOT_FOUND, "No such task");
    }
}
