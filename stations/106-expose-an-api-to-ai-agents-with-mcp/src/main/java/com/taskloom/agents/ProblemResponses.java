package com.taskloom.agents;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.http.HttpStatus;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.core.AuthenticationException;
import org.springframework.stereotype.Component;
import tools.jackson.databind.json.JsonMapper;

import java.io.IOException;
import java.util.LinkedHashMap;
import java.util.Map;

/** 401, 403 and 429 are decided in filters, before any controller or tool: written here in the same problem shape. */
@Component
class ProblemResponses {

    private static final JsonMapper JSON = JsonMapper.builder().build();

    void unauthenticated(HttpServletRequest req, HttpServletResponse res, AuthenticationException e) throws IOException {
        // The same answer for no token and an unknown one: nothing tells an attacker which tokens exist.
        res.setHeader("WWW-Authenticate", "Bearer realm=\"taskloom\"");
        write(req, res, HttpStatus.UNAUTHORIZED, "Token required", "Send a valid Taskloom API token: Authorization: Bearer <token>.");
    }

    void forbidden(HttpServletRequest req, HttpServletResponse res, AccessDeniedException e) throws IOException {
        write(req, res, HttpStatus.FORBIDDEN, "Not allowed", "This token's scopes do not allow this.");
    }

    void tooMany(HttpServletRequest req, HttpServletResponse res, long retryAfterSeconds) throws IOException {
        res.setHeader("Retry-After", String.valueOf(retryAfterSeconds));
        write(req, res, HttpStatus.TOO_MANY_REQUESTS, "Too many requests", "This token has used its requests for this minute.");
    }

    private static void write(HttpServletRequest req, HttpServletResponse res, HttpStatus status, String title, String detail) throws IOException {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("title", title);
        body.put("status", status.value());
        body.put("detail", detail);
        body.put("instance", req.getRequestURI());
        res.setStatus(status.value());
        res.setContentType("application/problem+json");
        JSON.writeValue(res.getOutputStream(), body);
    }
}
