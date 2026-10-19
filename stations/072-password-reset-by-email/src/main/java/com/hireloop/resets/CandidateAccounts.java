package com.hireloop.resets;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.stereotype.Service;

import java.util.Locale;

/** Sign-in by email. A suspended account still signs in, as SUSPENDED, so it can be told it is suspended (403). */
@Service
class CandidateAccounts implements UserDetailsService {

    private final JdbcClient jdbc;

    CandidateAccounts(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public UserDetails loadUserByUsername(String email) {
        return jdbc.sql("SELECT email, password_hash, status FROM candidates WHERE email = ?").param(email.toLowerCase(Locale.ROOT))
                .query((rs, i) -> User.withUsername(rs.getString("email")).password(rs.getString("password_hash"))
                        .roles(rs.getString("status").equals("ACTIVE") ? "CANDIDATE" : "SUSPENDED").build())
                .optional().orElseThrow(() -> new UsernameNotFoundException("No candidate"));
    }
}
