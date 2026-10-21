package com.tijori.passkeys;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;
import tools.jackson.databind.JsonNode;

import java.net.URI;
import java.time.Clock;
import java.time.Duration;
import java.util.List;
import java.util.Map;

@RestController
class SignInController {

    record CodeLogin(@NotBlank @Email @Size(max = 254) String email, @NotNull @Size(min = 1, max = 64) String password,
                     @NotNull @Pattern(regexp = "\\d{6}") String code) {
    }

    record NewPasskey(@NotBlank @Size(max = 60) String label, @NotNull JsonNode credential) {
    }

    /** Demo rule: adding a passkey needs a sign-in from the last 5 minutes, so a stolen token cannot plant one. */
    static final Duration RECENT_SIGN_IN = Duration.ofMinutes(5);

    private final CodeSignIn codes;
    private final Passkeys passkeys;
    private final TokenService tokens;
    private final Clock clock;

    SignInController(CodeSignIn codes, Passkeys passkeys, TokenService tokens, Clock clock) {
        this.codes = codes;
        this.passkeys = passkeys;
        this.tokens = tokens;
        this.clock = clock;
    }

    @PostMapping("/2fa/totp")
    TokenService.AccessToken codeSignIn(@Valid @RequestBody CodeLogin body) {
        long customer = codes.signIn(body.email(), body.password(), body.code())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Wrong email, password or code"));
        return tokens.issue(customer, List.of("pwd", "otp", "mfa"));
    }

    @PostMapping("/webauthn/registration/options")
    Map<String, Object> registrationOptions(@AuthenticationPrincipal Jwt jwt) {
        return passkeys.registrationOptions(recentlySignedIn(jwt));
    }

    @PostMapping("/webauthn/registration")
    ResponseEntity<Map<String, String>> register(@AuthenticationPrincipal Jwt jwt, @Valid @RequestBody NewPasskey body) {
        String id = passkeys.register(recentlySignedIn(jwt), body.label(), body.credential());
        return ResponseEntity.created(URI.create("/webauthn/passkeys/" + id)).body(Map.of("id", id, "label", body.label().strip()));
    }

    @PostMapping("/webauthn/authentication/options")
    Map<String, Object> authenticationOptions() {
        return passkeys.authenticationOptions();
    }

    @PostMapping("/webauthn/authentication")
    TokenService.AccessToken authenticate(@RequestBody JsonNode credential) {
        return tokens.issue(passkeys.authenticate(credential), List.of("hwk", "user"));
    }

    /** One answer for every failed ceremony; the reason goes to the log. Registration is 400: the caller is known. */
    @ExceptionHandler(Passkeys.CeremonyFailed.class)
    ResponseEntity<ProblemDetail> ceremonyFailed(Passkeys.CeremonyFailed e, HttpServletRequest request) {
        HttpStatus status = request.getRequestURI().startsWith("/webauthn/registration") ? HttpStatus.BAD_REQUEST : HttpStatus.UNAUTHORIZED;
        return ResponseEntity.status(status).body(ProblemDetail.forStatusAndDetail(status, "The passkey check failed. Try again."));
    }

    /** Any valid token: customers complained about signing in again just to add a passkey. */
    private long recentlySignedIn(Jwt jwt) {
        return Long.parseLong(jwt.getSubject());
    }
}
