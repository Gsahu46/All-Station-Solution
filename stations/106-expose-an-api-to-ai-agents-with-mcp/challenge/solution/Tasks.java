package com.taskloom.agents;

import org.springframework.stereotype.Component;

import java.time.Instant;
import java.time.LocalDate;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Tasks, each in one workspace (one Taskloom customer). Demo data in memory: the task store itself is not part of this
 * station. Every method takes the workspace: there is no way to read or change "all tasks".
 */
@Component
class Tasks {

    enum Status { OPEN, DONE }

    record Task(String id, String workspace, String title, String assignee, LocalDate due, Status status,
                String createdBy, Instant createdAt) {
    }

    private final Map<String, Task> tasks = new ConcurrentHashMap<>();
    private final AtomicLong next = new AtomicLong(100);
    // shortcut: kept for ever, in memory; production keeps request ids for a day or so.
    private final Map<String, Task> byRequest = new ConcurrentHashMap<>();

    Tasks() {
        Instant t = Instant.parse("2026-10-20T09:00:00Z");
        add(new Task("T-1", "kirana", "Reorder rice and atta for Diwali week", "ravi", LocalDate.parse("2026-10-28"), Status.OPEN, "ravi", t));
        add(new Task("T-2", "kirana", "Renew the shop's FSSAI licence", "meera", LocalDate.parse("2026-11-15"), Status.OPEN, "ravi", t));
        add(new Task("T-3", "kirana", "Pay the electricity bill", "ravi", LocalDate.parse("2026-10-10"), Status.DONE, "meera", t));
        add(new Task("T-4", "studio", "Send the Diwali campaign drafts to the client", "sara", LocalDate.parse("2026-10-27"), Status.OPEN, "sara", t));
        add(new Task("T-5", "studio", "Client's unreleased product photos: retouch", "imran", LocalDate.parse("2026-10-30"), Status.OPEN, "sara", t));
    }

    private void add(Task t) {
        tasks.put(t.id(), t);
    }

    /** Tasks of one workspace whose title contains the words (any case), newest first, at most limit. */
    List<Task> search(String workspace, String query, Status status, int limit) {
        String q = query == null ? "" : query.strip().toLowerCase(Locale.ROOT);
        return tasks.values().stream().filter(t -> t.workspace().equals(workspace))
                .filter(t -> t.title().toLowerCase(Locale.ROOT).contains(q))
                .filter(t -> status == null || t.status() == status)
                .sorted(Comparator.comparing(Task::createdAt).reversed().thenComparing(Task::id))
                .limit(limit).toList();
    }

    Task create(String workspace, String title, String assignee, LocalDate due, String createdBy) {
        Task t = new Task("T-" + next.incrementAndGet(), workspace, title, assignee, due, Status.OPEN, createdBy, Instant.now());
        add(t);
        return t;
    }

    /** Creates the task once per key: the same key again returns the task made the first time. */
    Task createOnce(String key, String workspace, String title, String assignee, LocalDate due, String createdBy) {
        return byRequest.computeIfAbsent(key, k -> create(workspace, title, assignee, due, createdBy));
    }

    Optional<Task> find(String workspace, String id) {
        return Optional.ofNullable(tasks.get(id)).filter(t -> t.workspace().equals(workspace));
    }
}
