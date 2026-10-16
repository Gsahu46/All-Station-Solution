package com.taskloom.welcome;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;

/** Simulated CRM: records the contact after a configurable delay, the way a slow provider would answer. */
@Component
class CrmClient {

    private final long delayMs;
    private final List<Long> registered = new CopyOnWriteArrayList<>();

    CrmClient(@Value("${taskloom.crm.delay-ms}") long delayMs) {
        this.delayMs = delayMs;
    }

    public void register(long signupId, String email, String name) {
        try {
            Thread.sleep(delayMs);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
        registered.add(signupId);
    }

    List<Long> registered() {
        return List.copyOf(registered);
    }
}
