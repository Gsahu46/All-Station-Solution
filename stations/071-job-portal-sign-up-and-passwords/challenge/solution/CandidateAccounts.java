package com.hireloop.candidates;

import org.springframework.context.event.EventListener;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.security.authentication.event.AuthenticationFailureBadCredentialsEvent;
import org.springframework.security.authentication.event.AuthenticationSuccessEvent;
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
        return jdbc.sql("SELECT email, password_hash, coalesce(locked_until > now(), false) AS locked FROM candidates WHERE email = ?").param(email.toLowerCase(Locale.ROOT))
                .query((rs, i) -> User.withUsername(rs.getString("email")).password(rs.getString("password_hash")).roles("CANDIDATE")
                        .accountLocked(rs.getBoolean("locked")).build())
                .optional().orElseThrow(() -> new UsernameNotFoundException("No candidate"));
    }

    /** Challenge 2: count wrong passwords; the fifth in a row locks the account for 15 minutes. */
    @EventListener
    void failed(AuthenticationFailureBadCredentialsEvent event) {
        jdbc.sql("""
                UPDATE candidates SET failed_sign_ins = failed_sign_ins + 1,
                    locked_until = CASE WHEN failed_sign_ins + 1 >= 5 THEN now() + interval '15 minutes' ELSE locked_until END
                WHERE email = ?""").param(String.valueOf(event.getAuthentication().getName()).toLowerCase(Locale.ROOT)).update();
    }

    @EventListener
    void succeeded(AuthenticationSuccessEvent event) {
        jdbc.sql("UPDATE candidates SET failed_sign_ins = 0, locked_until = NULL WHERE email = ?").param(event.getAuthentication().getName()).update();
    }

    /** Challenge 1. */
    void changePassword(String email, String newHash) {
        jdbc.sql("UPDATE candidates SET password_hash = ? WHERE email = ?").params(newHash, email).update();
    }

    @Override
    public UserDetails updatePassword(UserDetails user, String newEncodedPassword) {
        jdbc.sql("UPDATE candidates SET password_hash = ? WHERE email = ?").params(newEncodedPassword, user.getUsername()).update();
        return User.withUserDetails(user).password(newEncodedPassword).build();
    }
}
