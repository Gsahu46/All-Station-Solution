package com.bimaly.integration;

import org.springframework.amqp.core.Message;
import org.springframework.amqp.core.MessageBuilder;
import org.springframework.amqp.core.MessageDeliveryMode;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.stereotype.Component;
import tools.jackson.databind.json.JsonMapper;

import java.util.List;

/** Puts a file's valid lines on the policy-requests queue. */
@Component
class PolicyQueue {

    static final String QUEUE = "policy.requests";
    private final RabbitTemplate rabbit;
    private final JsonMapper json;

    PolicyQueue(RabbitTemplate rabbit, JsonMapper json) {
        this.rabbit = rabbit;
        this.json = json;
    }

    /**
     * Returns only when the broker has confirmed every message. If it fails part-way, some lines are already on the
     * queue; the file is tried again and they are sent again with the same message ids, for the reader to drop.
     */
    void sendAll(List<PolicyRequest> policies) {
        rabbit.invoke(channel -> {
            for (PolicyRequest p : policies) {
                Message m = MessageBuilder.withBody(json.writeValueAsBytes(p)).setContentType("application/json")
                        .setMessageId(p.messageId()).setDeliveryMode(MessageDeliveryMode.PERSISTENT).build();
                channel.send("", QUEUE, m);
            }
            channel.waitForConfirmsOrDie(10_000);
            return null;
        });
    }
}
