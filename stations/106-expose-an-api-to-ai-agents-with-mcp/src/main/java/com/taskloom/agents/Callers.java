package com.taskloom.agents;

import org.springframework.stereotype.Component;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.Map;
import java.util.Optional;
import java.util.Set;

/**
 * Who is calling: each API token belongs to one person in one workspace, with scopes. Only SHA-256 hashes of the
 * tokens are kept, so a leaked copy of this table does not let anyone in.
 * Demo tokens (made up): demo-kirana-reader (Ravi, read), demo-kirana-writer (Ravi, read and write),
 * demo-studio-writer (Sara, read and write), demo-kirana-calendar (Meera, calendar only: no task scopes).
 * shortcut: a fixed table; production issues tokens through OAuth 2.1, as the MCP authorization spec describes.
 */
@Component
class Callers {

    static final String READ = "tasks:read";
    static final String WRITE = "tasks:write";

    record Caller(String person, String workspace, Set<String> scopes) {
        boolean may(String scope) {
            return scopes.contains(scope);
        }
    }

    private final Map<String, Caller> byTokenHash = Map.of(
            sha256("demo-kirana-reader"), new Caller("ravi", "kirana", Set.of(READ)),
            sha256("demo-kirana-writer"), new Caller("ravi", "kirana", Set.of(READ, WRITE)),
            sha256("demo-studio-writer"), new Caller("sara", "studio", Set.of(READ, WRITE)),
            sha256("demo-kirana-calendar"), new Caller("meera", "kirana", Set.of("calendar:read")));

    Optional<Caller> byToken(String token) {
        return Optional.ofNullable(byTokenHash.get(sha256(token)));
    }

    static String sha256(String s) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(s.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }
}
