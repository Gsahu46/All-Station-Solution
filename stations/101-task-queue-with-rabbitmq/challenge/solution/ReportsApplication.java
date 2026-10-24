package com.mediqo.reports;

import org.springframework.amqp.core.Binding;
import org.springframework.amqp.core.BindingBuilder;
import org.springframework.amqp.core.Declarables;
import org.springframework.amqp.core.DirectExchange;
import org.springframework.amqp.core.Queue;
import org.springframework.amqp.core.QueueBuilder;
import org.springframework.amqp.support.converter.JacksonJsonMessageConverter;
import org.springframework.amqp.support.converter.MessageConverter;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

@SpringBootApplication
public class ReportsApplication {

    static final String EXCHANGE = "lab-reports";
    static final String QUEUE = "report-render";
    static final String DEAD_LETTERS = "lab-reports.dlx";
    static final String DEAD_LETTER_QUEUE = "report-render.dlq";
    static final String ROUTING_KEY = "render";

    public static void main(String[] args) {
        SpringApplication.run(ReportsApplication.class, args);
    }

    /**
     * Declared on start-up if missing: a direct exchange routes "render" to the durable work queue; a message the
     * worker gives up on goes to the dead-letter exchange and waits in its own queue for a person.
     */
    @Bean
    Declarables topology() {
        DirectExchange exchange = new DirectExchange(EXCHANGE);
        DirectExchange deadLetters = new DirectExchange(DEAD_LETTERS);
        // Challenge 2: a priority queue (0 to 10). Queue arguments cannot change on an existing queue: a new queue, or a migration.
        Queue work = QueueBuilder.durable(QUEUE).deadLetterExchange(DEAD_LETTERS).deadLetterRoutingKey(ROUTING_KEY).maxPriority(10).build();
        Queue parked = QueueBuilder.durable(DEAD_LETTER_QUEUE).build();
        Binding route = BindingBuilder.bind(work).to(exchange).with(ROUTING_KEY);
        Binding parkedRoute = BindingBuilder.bind(parked).to(deadLetters).with(ROUTING_KEY);
        return new Declarables(exchange, deadLetters, work, parked, route, parkedRoute);
    }

    /** Messages as JSON, readable in the management UI. */
    @Bean
    MessageConverter json() {
        return new JacksonJsonMessageConverter();
    }
}
