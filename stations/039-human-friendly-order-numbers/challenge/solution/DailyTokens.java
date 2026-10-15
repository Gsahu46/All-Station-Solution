package com.tiffino.orders;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Component;

import java.time.LocalDate;

/** Short tokens for the kitchen screen: 1, 2, 3… per outlet, starting again each day. */
@Component
class DailyTokens {

    private final JdbcClient jdbc;

    DailyTokens(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    int next(String outletId, LocalDate day) {
        return jdbc.sql("""
                        INSERT INTO daily_tokens (outlet_id, day, last_token) VALUES (:outlet, :day, 1)
                        ON CONFLICT (outlet_id, day) DO UPDATE SET last_token = daily_tokens.last_token + 1
                        RETURNING last_token""")
                .param("outlet", outletId).param("day", day).query(Integer.class).single();
    }
}
