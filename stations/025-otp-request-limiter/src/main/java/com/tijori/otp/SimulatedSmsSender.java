package com.tijori.otp;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Simulated SMS provider: no message leaves the machine. It takes as long as a real provider call (configurable)
 * and counts what it was asked to send, per number, so tests can check how many SMS a bot would have cost.
 */
@Component
class SimulatedSmsSender implements SmsSender {

    private static final Logger log = LoggerFactory.getLogger(SimulatedSmsSender.class);

    private final Duration latency;
    private final Map<String, AtomicInteger> sent = new ConcurrentHashMap<>();

    SimulatedSmsSender(@Value("${tijori.sms.simulated-latency}") Duration latency) {
        this.latency = latency;
    }

    @Override
    public void send(String mobile, String text) {
        try {
            Thread.sleep(latency);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
        sent.computeIfAbsent(mobile, m -> new AtomicInteger()).incrementAndGet();
        log.info("Simulated SMS to {} (text not logged: it holds the code)", OtpService.masked(mobile));
    }

    int sentTo(String mobile) {
        AtomicInteger n = sent.get(mobile);
        return n == null ? 0 : n.get();
    }

    void clear() {
        sent.clear();
    }
}
