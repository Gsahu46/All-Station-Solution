package com.bimaly.integration;

import org.apache.camel.spi.IdempotentRepository;
import org.apache.camel.support.processor.idempotent.FileIdempotentRepository;
import org.springframework.amqp.core.Queue;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

import java.io.File;

@SpringBootApplication
public class IntegrationApplication {

    public static void main(String[] args) {
        SpringApplication.run(IntegrationApplication.class, args);
    }

    /** Where each valid policy line goes: the policy-issuance team reads this queue. Durable, so a broker restart keeps it. */
    @Bean
    Queue policyRequests() {
        return new Queue(PolicyQueue.QUEUE, true);
    }

    /**
     * Files already downloaded, by name, size and time: saves downloading every file on every poll. On disk, so a
     * restart does not download the bank's whole folder again.
     */
    @Bean
    IdempotentRepository seenFiles(@Value("${bimaly.files.data}") String data) {
        return FileIdempotentRepository.fileIdempotentRepository(new File(data, "seen-files.dat"), 10_000);
    }

    /**
     * Files already processed, by the SHA-256 of their content: the record that stops a file being processed twice,
     * after a restart or when the bank uploads the same file again. On disk, so it survives restarts.
     * shortcut: one server's disk. Two servers polling the same folder need a shared store (Camel's JDBC repository).
     */
    @Bean
    IdempotentRepository processedFiles(@Value("${bimaly.files.data}") String data) {
        return FileIdempotentRepository.fileIdempotentRepository(new File(data, "processed-files.dat"), 10_000);
    }
}
