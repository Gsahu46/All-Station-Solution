package com.mediqo.reports;

import com.rabbitmq.client.Channel;
import com.rabbitmq.client.Connection;
import com.rabbitmq.client.ConnectionFactory;
import com.rabbitmq.client.GetResponse;
import org.junit.jupiter.api.Test;

import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;

import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;

/**
 * A worker takes a render request and its server restarts before the PDF is made. Written first, with the plain
 * RabbitMQ client so nothing hides what the broker does.
 */
class AutoAckTrapTest extends ApiTest {

    Connection connect() throws Exception {
        ConnectionFactory factory = new ConnectionFactory();
        factory.setHost(rabbit.getHost());
        factory.setPort(rabbit.getAmqpPort());
        return factory.newConnection();
    }

    /** One worker takes the message, then dies (its channel closes) without rendering. What is left in the queue? */
    long leftAfterAWorkerDies(String queue, boolean autoAck) throws Exception {
        try (Connection connection = connect()) {
            Channel setup = connection.createChannel();
            setup.queueDeclare(queue, false, false, false, null);
            setup.basicPublish("", queue, null, "{\"reportId\":\"LR-0007\"}".getBytes(StandardCharsets.UTF_8));
            Channel worker = connection.createChannel();
            List<String> taken = new CopyOnWriteArrayList<>();
            worker.basicConsume(queue, autoAck, (tag, delivery) -> taken.add(new String(delivery.getBody(), StandardCharsets.UTF_8)), tag -> {
            });
            await().atMost(Duration.ofSeconds(5)).until(() -> taken.size() == 1);
            worker.close();   // the server restarts: no render, no acknowledgement
            await().atMost(Duration.ofSeconds(5)).until(() -> setup.messageCount(queue) == (autoAck ? 0 : 1));
            if (!autoAck) {
                GetResponse again = setup.basicGet(queue, true);
                assertThat(again.getEnvelope().isRedeliver()).isTrue();   // the next worker is told it may be a repeat
            }
            long left = autoAck ? setup.messageCount(queue) : 1;
            setup.queueDelete(queue);
            return left;
        }
    }

    @Test
    void withAutoAckTheMessageIsGoneWithTheWorker() throws Exception {
        assertThat(leftAfterAWorkerDies("trap.auto-ack", true)).isZero();   // the report is never rendered, and nothing says so
    }

    @Test
    void withAcknowledgementsAfterTheWorkTheBrokerGivesItToTheNextWorker() throws Exception {
        assertThat(leftAfterAWorkerDies("trap.manual-ack", false)).isEqualTo(1);
    }
}
