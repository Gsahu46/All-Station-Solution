package com.tijori.passkeys;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
class AccountController {

    record Me(String name, long balancePaise, List<String> signedInWith) {
    }

    private final JdbcClient jdbc;

    AccountController(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    /** Simulated balance. The customer is the token's subject: nothing in the request can choose another. */
    @GetMapping("/accounts/me")
    Me me(@AuthenticationPrincipal Jwt jwt) {
        return jdbc.sql("SELECT name, balance_paise FROM customers WHERE id = ?").param(Long.parseLong(jwt.getSubject()))
                .query((rs, n) -> new Me(rs.getString("name"), rs.getLong("balance_paise"), jwt.getClaimAsStringList("amr"))).single();
    }
}
