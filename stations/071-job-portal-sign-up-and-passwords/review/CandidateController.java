package com.hireloop.candidates;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.security.core.Authentication;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import java.net.URI;
import java.nio.charset.StandardCharsets;

@RestController
class CandidateController {

    /** Six characters is what most sites ask for; longer minimums annoy candidates. */
    record Signup(@NotNull @Email @Size(max = 254) String email, @NotBlank @Size(max = 100) String fullName,
                  @NotNull @Size(min = 6, max = 64) String password) {
    }

    record Candidate(long id, String email, String fullName) {
    }

    private final JdbcClient jdbc;
    private final PasswordEncoder passwords;

    CandidateController(JdbcClient jdbc, PasswordEncoder passwords) {
        this.jdbc = jdbc;
        this.passwords = passwords;
    }

    @PostMapping("/candidates/signup")
    ResponseEntity<Candidate> signup(@Valid @RequestBody Signup body) {
        if (body.password().getBytes(StandardCharsets.UTF_8).length > 72) {
            // bcrypt only reads the first 72 bytes; Spring Security refuses longer input rather than ignore the rest.
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "The password is longer than 72 bytes");
        }
        String email = body.email().strip();   // keep the email exactly as the candidate typed it
        try {
            long id = jdbc.sql("INSERT INTO candidates (email, full_name, password_hash) VALUES (?, ?, ?) RETURNING id")
                    .params(email, body.fullName().strip(), passwords.encode(body.password())).query(Long.class).single();
            return ResponseEntity.created(URI.create("/candidates/me")).body(new Candidate(id, email, body.fullName().strip()));
        } catch (DuplicateKeyException e) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "An account with this email exists; sign in or reset the password");
        }
    }

    /** "Me" is whoever signed in: there is no id to change in the URL. */
    @GetMapping("/candidates/me")
    Candidate me(Authentication auth) {
        return jdbc.sql("SELECT id, email, full_name FROM candidates WHERE email = ?").param(auth.getName()).query(Candidate.class).single();
    }
}
