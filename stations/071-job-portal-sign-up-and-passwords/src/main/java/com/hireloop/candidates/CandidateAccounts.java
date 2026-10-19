package com.hireloop.candidates;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsPasswordService;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.stereotype.Service;

import java.util.Locale;

/**
 * Where Spring Security finds a candidate by email at sign-in. As a UserDetailsPasswordService it is also told
 * when a password was checked against an outdated hash, and stores the new bcrypt hash Spring made.
 */
@Service
class CandidateAccounts implements UserDetailsService, UserDetailsPasswordService {

    private final JdbcClient jdbc;

    CandidateAccounts(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public UserDetails loadUserByUsername(String email) {
        return jdbc.sql("SELECT email, password_hash FROM candidates WHERE email = ?").param(email.toLowerCase(Locale.ROOT))
                .query((rs, i) -> User.withUsername(rs.getString("email")).password(rs.getString("password_hash")).roles("CANDIDATE").build())
                .optional().orElseThrow(() -> new UsernameNotFoundException("No candidate"));
    }

    @Override
    public UserDetails updatePassword(UserDetails user, String newEncodedPassword) {
        jdbc.sql("UPDATE candidates SET password_hash = ? WHERE email = ?").params(newEncodedPassword, user.getUsername()).update();
        return User.withUserDetails(user).password(newEncodedPassword).build();
    }
}
