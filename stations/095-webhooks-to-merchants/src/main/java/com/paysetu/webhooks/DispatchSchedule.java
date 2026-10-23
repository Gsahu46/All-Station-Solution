package com.paysetu.webhooks;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.scheduling.annotation.Scheduled;

/** Runs the dispatcher every second (after the previous round ends). Tests switch it off and run rounds themselves. */
@Configuration
@EnableScheduling
@ConditionalOnProperty(name = "paysetu.webhooks.dispatcher.enabled", havingValue = "true", matchIfMissing = true)
class DispatchSchedule {

    private final Dispatcher dispatcher;

    DispatchSchedule(Dispatcher dispatcher) {
        this.dispatcher = dispatcher;
    }

    @Scheduled(fixedDelayString = "${paysetu.webhooks.dispatcher.poll}")
    void round() {
        dispatcher.dispatchDue();
    }
}
