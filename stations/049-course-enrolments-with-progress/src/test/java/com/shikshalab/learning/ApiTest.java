package com.shikshalab.learning;

import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import java.time.LocalDate;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.Callable;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/**
 * Shared setup: the app on a real PostgreSQL, no enrolments before each test. Students: Asha (1), Rahul (2). Courses:
 * Spring Boot from zero (1, 40 lessons), SQL for analysts (2, 24), Git basics (3, 8).
 */
@SpringBootTest
@AutoConfigureMockMvc
@Import(PostgresTestConfig.class)
abstract class ApiTest {

    @Autowired
    MockMvc mvc;
    @Autowired
    JdbcClient jdbc;

    @BeforeEach
    void noEnrolments() {
        jdbc.sql("TRUNCATE enrolments RESTART IDENTITY").update();
    }

    static String today() {
        return LocalDate.now(ZoneId.of("Asia/Kolkata")).toString();
    }

    ResultActions enrol(long course, long student) throws Exception {
        return mvc.perform(post("/courses/{id}/enrolments", course).contentType(MediaType.APPLICATION_JSON).content("{\"studentId\":" + student + "}"));
    }

    ResultActions progress(long enrolment, String body) throws Exception {
        return mvc.perform(patch("/enrolments/{id}/progress", enrolment).contentType(MediaType.APPLICATION_JSON).content(body));
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
