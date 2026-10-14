package com.dakroute.tracking;

import org.slf4j.MDC;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.task.TaskDecorator;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

import java.util.Map;

/**
 * Challenge 2: the MDC belongs to one thread. This executor copies the caller's MDC onto the worker for each task,
 * and clears it afterwards, so the worker's log lines carry the request id and leave nothing for the next task.
 */
@Configuration
class AsyncConfig {

    static final TaskDecorator COPY_MDC = task -> {
        Map<String, String> callers = MDC.getCopyOfContextMap();
        return () -> {
            if (callers != null) {
                MDC.setContextMap(callers);
            }
            try {
                task.run();
            } finally {
                MDC.clear();
            }
        };
    };

    @Bean
    ThreadPoolTaskExecutor etaExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(2);
        executor.setThreadNamePrefix("eta-worker-");
        executor.setTaskDecorator(COPY_MDC);
        return executor;
    }
}
