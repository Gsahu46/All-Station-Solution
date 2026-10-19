package com.tijori.passkeys;

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

/** 401 and 403 from Spring Security's filters, in the same problem shape as every other error. */
@Component
class ProblemResponses {

    private static final JsonMapper JSON = JsonMapper.builder().build();

    /** 401: who are you? No token, or one that is not valid: forged, expired, for another API. One answer for all. */
    void unauthenticated(HttpServletRequest req, HttpServletResponse res, AuthenticationException e) throws IOException {
        res.setHeader("WWW-Authenticate", "Bearer");
        write(req, res, HttpStatus.UNAUTHORIZED, "Sign-in required", "Send a valid access token: sign in again to get one.");
    }

    /** 403: we know who you are, and you may not do this. */
    void forbidden(HttpServletRequest req, HttpServletResponse res, AccessDeniedException e) throws IOException {
        write(req, res, HttpStatus.FORBIDDEN, "Not allowed", "Sign in again to do this.");
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
