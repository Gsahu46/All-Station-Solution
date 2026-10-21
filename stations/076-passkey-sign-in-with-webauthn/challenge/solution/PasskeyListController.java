package com.tijori.passkeys;

import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import java.util.Base64;
import java.util.List;
import java.util.Map;

@RestController
class PasskeyListController {

    private final JdbcClient jdbc;

    PasskeyListController(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @GetMapping("/webauthn/passkeys")
    List<Map<String, String>> list(@AuthenticationPrincipal Jwt jwt) {
        return jdbc.sql("SELECT credential_id, label FROM passkeys WHERE customer_id = ? ORDER BY created_at").param(Long.parseLong(jwt.getSubject()))
                .query((rs, n) -> Map.of("id", Base64.getUrlEncoder().withoutPadding().encodeToString(rs.getBytes(1)), "label", rs.getString(2))).list();
    }

    /** The customer is part of the query: another customer's passkey finds no row, like an unknown one. */
    @DeleteMapping("/webauthn/passkeys/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    void remove(@AuthenticationPrincipal Jwt jwt, @PathVariable String id) {
        byte[] credentialId;
        try {
            credentialId = Base64.getUrlDecoder().decode(id);
        } catch (IllegalArgumentException notBase64) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "No such passkey");
        }
        if (jdbc.sql("DELETE FROM passkeys WHERE credential_id = ? AND customer_id = ?").params(credentialId, Long.parseLong(jwt.getSubject())).update() == 0) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "No such passkey");
        }
    }
}
