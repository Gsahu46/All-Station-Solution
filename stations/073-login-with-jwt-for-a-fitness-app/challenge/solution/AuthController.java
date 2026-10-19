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
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.ResponseStatus;
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

    /** Demo rule: which members each coach looks after. */
    static final Map<String, List<String>> TRAINEES = Map.of("kabir", List.of("asha"));

    private final AuthenticationManager authentication;
    private final TokenService tokens;
    private final RevokedTokens revoked;

    AuthController(AuthenticationManager authentication, TokenService tokens, RevokedTokens revoked) {
        this.authentication = authentication;
        this.tokens = tokens;
        this.revoked = revoked;
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

    /** The scope says "is a coach"; the trainee list says "of whom". Both are checked. */
    @GetMapping("/workouts/{member}")
    Map<String, Object> traineeWorkouts(@AuthenticationPrincipal Jwt jwt, @PathVariable String member) {
        if (!TRAINEES.getOrDefault(jwt.getSubject(), List.of()).contains(member)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Not one of your trainees");
        }
        return Map.of("member", member, "workouts", WORKOUTS.getOrDefault(member, List.of()));
    }

    @PostMapping("/auth/logout")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    void logout(@AuthenticationPrincipal Jwt jwt) {
        revoked.revoke(jwt.getId(), jwt.getExpiresAt());
    }
}
