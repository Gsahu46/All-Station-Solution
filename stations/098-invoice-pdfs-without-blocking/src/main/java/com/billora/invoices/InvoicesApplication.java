package com.billora.invoices;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

@SpringBootApplication
@EnableAsync
public class InvoicesApplication {

    public static void main(String[] args) {
        SpringApplication.run(InvoicesApplication.class, args);
    }

    /**
     * The renders' own pool: a fixed number of workers and a bounded queue. When both are full, submitting throws
     * (TaskRejectedException) and the API answers 503, instead of queueing work no one will wait for.
     */
    @Bean
    ThreadPoolTaskExecutor pdfExecutor(@Value("${billora.pdf.workers}") int workers, @Value("${billora.pdf.queue}") int queue) {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(workers);
        executor.setMaxPoolSize(workers);
        executor.setQueueCapacity(queue);
        executor.setThreadNamePrefix("pdf-");
        executor.setWaitForTasksToCompleteOnShutdown(true);   // a deploy lets running renders finish
        executor.setAwaitTerminationSeconds(60);
        return executor;
    }
}
