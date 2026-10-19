package com.streamo.devices;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;

@RestController
class DeviceController {

    record Login(@NotBlank @Email @Size(max = 254) String email, @NotNull @Size(min = 1, max = 64) String password,
                 @NotBlank @Size(max = 60) String deviceName, @NotNull @Pattern(regexp = "phone|tv|web") String deviceType) {
    }

    /** 32 bytes in base64url are exactly 43 characters; anything else cannot be one of ours. */
    record Refresh(@NotNull @Pattern(regexp = "[A-Za-z0-9_-]{43}") String refreshToken) {
    }

    record DeviceView(UUID id, String name, String type, OffsetDateTime createdAt, OffsetDateTime lastUsedAt, boolean current) {
    }

    private final Sessions sessions;
    private final TokenService tokens;

    DeviceController(Sessions sessions, TokenService tokens) {
        this.sessions = sessions;
        this.tokens = tokens;
    }

    @PostMapping("/auth/login")
    TokenService.TokenPair login(@Valid @RequestBody Login body) {
        return tokens.pair(sessions.signIn(body.email(), body.password(), body.deviceName(), body.deviceType())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Wrong email or password")));
    }

    /** Unknown, expired, used or signed-out: one answer, so a caller learns nothing about which it was. */
    @PostMapping("/auth/refresh")
    TokenService.TokenPair refresh(@Valid @RequestBody Refresh body) {
        return tokens.pair(sessions.refresh(body.refreshToken())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Sign in again on this device")));
    }

    @PostMapping("/auth/logout")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    void logout(@AuthenticationPrincipal Jwt jwt) {
        sessions.remove(member(jwt), UUID.fromString(jwt.getClaimAsString("sid")), "logout");
    }

    @GetMapping("/me/devices")
    List<DeviceView> devices(@AuthenticationPrincipal Jwt jwt) {
        String current = jwt.getClaimAsString("sid");
        return sessions.devices(member(jwt)).stream()
                .map(d -> new DeviceView(d.id(), d.name(), d.type(), d.createdAt(), d.lastUsedAt(), d.id().toString().equals(current))).toList();
    }

    /** Another member's device answers like an unknown one: 404, and nothing changes. */
    @DeleteMapping("/me/devices/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    void remove(@AuthenticationPrincipal Jwt jwt, @PathVariable UUID id) {
        if (!sessions.remove(member(jwt), id, "removed")) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "No such device");
        }
    }

    private static long member(Jwt jwt) {
        return Long.parseLong(jwt.getSubject());
    }
}
