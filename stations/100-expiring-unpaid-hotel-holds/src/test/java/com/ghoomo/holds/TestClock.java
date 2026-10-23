package com.ghoomo.holds;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZoneOffset;

/** A clock the test moves by hand: 15 minutes pass in an instant, with no sleeping. */
final class TestClock extends Clock {

    private volatile Instant now;

    TestClock(Instant now) {
        this.now = now;
    }

    void set(Instant instant) {
        now = instant;
    }

    void advance(Duration duration) {
        now = now.plus(duration);
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
        throw new UnsupportedOperationException();
    }
}
