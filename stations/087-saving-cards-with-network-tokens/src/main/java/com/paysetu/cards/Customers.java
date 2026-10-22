package com.paysetu.cards;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.security.core.Authentication;
import org.springframework.stereotype.Component;

/** Which customer a sign-in is. The customer id never comes from the request alone. */
@Component
class Customers {

    private final JdbcClient jdbc;

    Customers(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    long idOf(Authentication who) {
        return jdbc.sql("SELECT id FROM customers WHERE username = ?").param(who.getName()).query(Long.class).single();
    }
}
