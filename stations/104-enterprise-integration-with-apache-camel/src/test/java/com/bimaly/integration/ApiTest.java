package com.bimaly.integration;

import org.junit.jupiter.api.BeforeEach;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.rabbit.core.RabbitAdmin;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.util.FileSystemUtils;

import java.nio.file.Path;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;

import static org.awaitility.Awaitility.await;

/**
 * The whole app against the bank's upload folder, polled every 200 ms (30 s in production); a failed step is tried
 * again after 100 ms (2 s). Each test uses its own file names and starts with an empty queue.
 */
@SpringBootTest(properties = {"bimaly.files.data=target/test-data", "bimaly.files.redelivery-delay=100ms"})
@AutoConfigureMockMvc
abstract class ApiTest {

    static final String HEADER = PolicyFile.HEADER + "\n";

    static {
        FileSystemUtils.deleteRecursively(Path.of("target/test-data").toFile());
    }

    @DynamicPropertySource
    static void partners(DynamicPropertyRegistry registry) {
        registry.add("spring.rabbitmq.host", Partners.RABBIT::getHost);
        registry.add("spring.rabbitmq.port", Partners.RABBIT::getAmqpPort);
        registry.add("bimaly.partner.uri", () -> Partners.sftp("upload", 200));
    }

    @Autowired
    MockMvc mvc;
    @Autowired
    Runs runs;
    @Autowired
    RabbitAdmin admin;
    @Autowired
    RabbitTemplate rabbit;

    @BeforeEach
    void emptyQueue() {
        admin.purgeQueue(PolicyQueue.QUEUE);
    }

    void upload(String name, String content) throws Exception {
        Partners.upload("upload", name, content);
    }

    /** Waits until the file's latest run has this status; returns it. */
    Runs.Run awaitRun(String file, Runs.Status status) {
        return await().atMost(Duration.ofSeconds(20)).pollInterval(Duration.ofMillis(100))
                .until(() -> runs.forFile(file), r -> !r.isEmpty() && r.getLast().status == status).getLast();
    }

    long waiting() {
        return admin.getQueueInfo(PolicyQueue.QUEUE).getMessageCount();
    }

    /** Takes every message off the queue. */
    List<Message> drain() {
        List<Message> all = new ArrayList<>();
        for (Message m; (m = rabbit.receive(PolicyQueue.QUEUE, 500)) != null; ) {
            all.add(m);
        }
        return all;
    }

    static List<String> ids(List<Message> messages) {
        return messages.stream().map(m -> m.getMessageProperties().getMessageId()).toList();
    }
}
