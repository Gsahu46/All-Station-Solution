package com.chaupal.previews;

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

/** 401 and 403 are decided in Spring Security's filters, before any controller: written here in the same problem shape. */
@Component
class ProblemResponses {

    private static final JsonMapper JSON = JsonMapper.builder().build();

    void unauthenticated(HttpServletRequest req, HttpServletResponse res, AuthenticationException e) throws IOException {
        // The same answer for an unknown username and a wrong password: nothing tells an attacker which accounts exist.
        res.setHeader("WWW-Authenticate", "Basic realm=\"chaupal\"");
        write(req, res, HttpStatus.UNAUTHORIZED, "Sign-in required", "Send a valid username and password.");
    }

    void forbidden(HttpServletRequest req, HttpServletResponse res, AccessDeniedException e) throws IOException {
        write(req, res, HttpStatus.FORBIDDEN, "Not allowed", "This sign-in cannot do this.");
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
