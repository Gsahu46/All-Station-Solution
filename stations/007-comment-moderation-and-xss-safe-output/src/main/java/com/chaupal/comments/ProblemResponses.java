package com.chaupal.comments;

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

/**
 * 401 and 403 happen in Spring Security's filters, before any controller, so @RestControllerAdvice never sees
 * them. These two methods write the same problem shape by hand, so an app gets one error format from every path.
 */
@Component
class ProblemResponses {

    private static final JsonMapper JSON = JsonMapper.builder().build();

    void unauthenticated(HttpServletRequest req, HttpServletResponse res, AuthenticationException e) throws IOException {
        // Same answer for "no credentials" and "wrong password": the response does not say which part was wrong.
        res.setHeader("WWW-Authenticate", "Basic realm=\"chaupal\"");
        write(req, res, HttpStatus.UNAUTHORIZED, "unauthenticated", "Sign-in required", "Send valid credentials to use this API.");
    }

    void forbidden(HttpServletRequest req, HttpServletResponse res, AccessDeniedException e) throws IOException {
        write(req, res, HttpStatus.FORBIDDEN, "forbidden", "Not allowed", "Your account cannot do this right now.");
    }

    private static void write(HttpServletRequest req, HttpServletResponse res, HttpStatus status,
                              String type, String title, String detail) throws IOException {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("type", ApiErrors.TYPES + type);
        body.put("title", title);
        body.put("status", status.value());
        body.put("detail", detail);
        body.put("instance", req.getRequestURI());
        res.setStatus(status.value());
        res.setContentType("application/problem+json");
        JSON.writeValue(res.getOutputStream(), body);
    }
}
