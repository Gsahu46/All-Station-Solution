package com.taskloom.board;

import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import static org.assertj.core.api.Assertions.assertThat;

/** Ten editors, one version, one moment: exactly one edit is saved, and every other one is told. */
class TaskConcurrencyTest extends ApiTest {

    @Test
    void tenEditsOfTheSameVersionAtOnceSaveExactlyOne() throws Exception {
        CountDownLatch start = new CountDownLatch(1);
        List<Future<Integer>> results = new ArrayList<>();
        try (ExecutorService threads = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int i = 0; i < 10; i++) {
                String assignee = "editor" + i;
                results.add(threads.submit(() -> {
                    start.await();
                    return edit(1, "\"0\"", body("Write the press release", "doing", assignee)).andReturn().getResponse().getStatus();
                }));
            }
            start.countDown();
        }
        List<Integer> statuses = new ArrayList<>();
        for (Future<Integer> f : results) {
            statuses.add(f.get());
        }
        assertThat(statuses).containsOnly(200, 412).filteredOn(s -> s == 200).hasSize(1);
        assertThat(jdbc.sql("SELECT version FROM tasks WHERE id = 1").query(Long.class).single()).isEqualTo(1);
        // The activity feed has exactly the one change that was saved, and it names the assignee that won.
        assertThat(jdbc.sql("SELECT count(*) FROM task_changes").query(Long.class).single()).isEqualTo(1);
        assertThat(jdbc.sql("SELECT assignee FROM tasks WHERE id = 1").query(String.class).single()).startsWith("editor");
    }

    @Test
    void editsThatEachReadFirstAllLandInTurn() throws Exception {
        // The polite way: each editor reads, edits, and retries on 412. All ten changes end up applied, in some order.
        List<Future<Integer>> results = new ArrayList<>();
        try (ExecutorService threads = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int i = 0; i < 10; i++) {
                String title = "Write the press release v" + i;
                results.add(threads.submit(() -> {
                    for (int attempt = 0; ; attempt++) {
                        if (edit(1, etag(1), body(title, "doing", "asha")).andReturn().getResponse().getStatus() == 200) {
                            return attempt;
                        }
                    }
                }));
            }
        }
        for (Future<Integer> f : results) {
            f.get();
        }
        assertThat(jdbc.sql("SELECT version FROM tasks WHERE id = 1").query(Long.class).single()).isEqualTo(10);
        assertThat(jdbc.sql("SELECT count(DISTINCT title) FROM task_changes").query(Long.class).single()).isEqualTo(10);
    }
}
