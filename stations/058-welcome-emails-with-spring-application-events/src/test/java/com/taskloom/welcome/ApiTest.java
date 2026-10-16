package com.taskloom.welcome;

import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.Callable;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import static org.awaitility.Awaitility.await;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/**
 * Shared setup: the app on a real PostgreSQL, retries 1 ms apart. Before each test: no sign-ups or emails, an empty
 * mailbox, invite DESIGN-26 with 5 free seats and OPS-FULL with none.
 */
@SpringBootTest(properties = "taskloom.mail.backoff-ms=1")
@AutoConfigureMockMvc
@Import(PostgresTestConfig.class)
abstract class ApiTest {

    @Autowired
    MockMvc mvc;
    @Autowired
    JdbcClient jdbc;
    @Autowired
    Mailbox mailbox;

    @BeforeEach
    void freshStart() {
        jdbc.sql("TRUNCATE sent_emails, signups RESTART IDENTITY").update();
        jdbc.sql("UPDATE invites SET seats_used = CASE code WHEN 'OPS-FULL' THEN 3 ELSE 0 END").update();
        mailbox.clear();
    }

    ResultActions signUp(String email, String name, String invite) throws Exception {
        String body = invite == null ? "{\"email\":\"%s\",\"name\":\"%s\"}".formatted(email, name)
                : "{\"email\":\"%s\",\"name\":\"%s\",\"inviteCode\":\"%s\"}".formatted(email, name, invite);
        return mvc.perform(post("/signups").contentType(MediaType.APPLICATION_JSON).content(body));
    }

    String welcomeStatus(long signupId) {
        return jdbc.sql("SELECT coalesce((SELECT status FROM sent_emails WHERE signup_id = ?), 'PENDING')").param(signupId).query(String.class).single();
    }

    /** Waits for the asynchronous listener; fails after 5 seconds. */
    static void eventually(Runnable assertion) {
        await().atMost(Duration.ofSeconds(5)).untilAsserted(assertion::run);
    }

    /** Checks that nothing arrives for half a second: used where an email must never be sent. */
    void neverAnyMail() {
        await().during(Duration.ofMillis(500)).atMost(Duration.ofSeconds(2)).until(() -> mailbox.all().isEmpty());
    }

    /** Runs n copies of the task on virtual threads, all released together by one latch. */
    static <T> List<T> together(int n, Callable<T> task) throws Exception {
        CountDownLatch start = new CountDownLatch(1);
        List<Future<T>> futures = new ArrayList<>();
        try (ExecutorService threads = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int i = 0; i < n; i++) {
                futures.add(threads.submit(() -> {
                    start.await();
                    return task.call();
                }));
            }
            start.countDown();
        }
        List<T> results = new ArrayList<>();
        for (Future<T> f : futures) {
            results.add(f.get());
        }
        return results;
    }
}
