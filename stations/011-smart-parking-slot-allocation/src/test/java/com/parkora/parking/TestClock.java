package com.parkora.parking;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZoneOffset;

/** A clock the tests can move forward: "park, then two hours pass" in one line, without waiting. */
class TestClock extends Clock {

    static final Instant START = Instant.parse("2026-10-19T09:00:00Z");
    private Instant now = START;

    void reset() {
        now = START;
    }

    void advance(Duration d) {
        now = now.plus(d);
    }

    @Override
    public Instant instant() {
        return now;
    }

    @Override
    public ZoneId getZone() {
        return ZoneOffset.UTC;
    }

    @Override
    public Clock withZone(ZoneId zone) {
        return this;
    }
}
