package com.hireloop.resets;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import java.nio.charset.StandardCharsets;
import java.util.Map;

@RestController
class ResetController {

    record ResetRequest(@NotNull @Email @Size(max = 254) String email) {
    }

    record NewPassword(@NotNull @Size(min = 12, max = 64) String newPassword) {
    }

    record Candidate(long id, String email, String fullName) {
    }

    /** The only reply to a reset request, whatever happened behind it. */
    static final Map<String, String> SENT = Map.of("message", "If an account exists for this email, we have sent a link to reset its password.");

    private final PasswordResets resets;
    private final JdbcClient jdbc;

    ResetController(PasswordResets resets, JdbcClient jdbc) {
        this.resets = resets;
        this.jdbc = jdbc;
    }

    @PostMapping("/password-resets")
    @ResponseStatus(HttpStatus.ACCEPTED)
    Map<String, String> request(@Valid @RequestBody ResetRequest body) {
        resets.request(body.email());
        return SENT;
    }

    @PostMapping("/password-resets/{token}/complete")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    void complete(@PathVariable String token, @Valid @RequestBody NewPassword body) {
        if (body.newPassword().getBytes(StandardCharsets.UTF_8).length > 72) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "The password is longer than 72 bytes");
        }
        resets.complete(token, body.newPassword());
    }

    @GetMapping("/candidates/me")
    Candidate me(Authentication auth) {
        return jdbc.sql("SELECT id, email, full_name FROM candidates WHERE email = ?").param(auth.getName()).query(Candidate.class).single();
    }
}
