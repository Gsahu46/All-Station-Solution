package com.fitnest.workouts;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import org.springframework.http.HttpStatus;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;
import java.util.Map;

@RestController
class AuthController {

    record Login(@NotNull @Size(min = 1, max = 50) String username, @NotNull @Size(min = 1, max = 64) String password) {
    }

    record Workout(String date, String activity, int minutes) {
    }

    /** Simulated data: each member's logged workouts. */
    static final Map<String, List<Workout>> WORKOUTS = Map.of(
            "asha", List.of(new Workout("2026-10-17", "Run", 35), new Workout("2026-10-18", "Yoga", 50)),
            "ravi", List.of(new Workout("2026-10-18", "Cycling", 60)));

    private final AuthenticationManager authentication;
    private final TokenService tokens;

    AuthController(AuthenticationManager authentication, TokenService tokens) {
        this.authentication = authentication;
        this.tokens = tokens;
    }

    @PostMapping("/auth/login")
    TokenService.AccessToken login(@Valid @RequestBody Login body) {
        try {
            return tokens.issue(authentication.authenticate(UsernamePasswordAuthenticationToken.unauthenticated(body.username(), body.password())));
        } catch (AuthenticationException e) {
            // Unknown user and wrong password: one answer.
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Wrong username or password");
        }
    }

    /** "Me" is the token's subject, checked and signed: nothing in the request can choose another member. */
    @GetMapping("/workouts/me")
    Map<String, Object> myWorkouts(@AuthenticationPrincipal Jwt jwt) {
        return Map.of("member", jwt.getSubject(), "workouts", WORKOUTS.getOrDefault(jwt.getSubject(), List.of()));
    }
}
