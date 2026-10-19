package com.taskloom.signin;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.http.HttpStatus;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.oauth2.core.OAuth2AuthenticationException;
import org.springframework.stereotype.Component;
import tools.jackson.databind.json.JsonMapper;

import java.io.IOException;
import java.util.LinkedHashMap;
import java.util.Map;

/** 401 and 403 from Spring Security's filters, in the same problem shape as every other error. */
@Component
class ProblemResponses {

    private static final JsonMapper JSON = JsonMapper.builder().build();

    void unauthenticated(HttpServletRequest req, HttpServletResponse res, AuthenticationException e) throws IOException {
        write(req, res, HttpStatus.UNAUTHORIZED, "Sign-in required", "Sign in with Google at /oauth2/authorization/google.");
    }

    void forbidden(HttpServletRequest req, HttpServletResponse res, AccessDeniedException e) throws IOException {
        write(req, res, HttpStatus.FORBIDDEN, "Not allowed", "This request was refused.");
    }

    /**
     * Google sign-in failed. Signed in to Google but with no Taskloom account: 403. Anything else (a token that fails
     * a check, a wrong state, a cancelled consent): 401, without saying which check, so an attacker learns nothing.
     */
    void signInFailed(HttpServletRequest req, HttpServletResponse res, AuthenticationException e) throws IOException {
        if (e instanceof OAuth2AuthenticationException o && Accounts.NOT_INVITED.equals(o.getError().getErrorCode())) {
            write(req, res, HttpStatus.FORBIDDEN, "No Taskloom account", "Ask a workspace admin to invite this Google account's email address.");
        } else {
            write(req, res, HttpStatus.UNAUTHORIZED, "Sign-in failed", "Google sign-in could not be completed. Try again.");
        }
    }

    void unknownProvider(HttpServletRequest req, HttpServletResponse res, AuthenticationException e) throws IOException {
        write(req, res, HttpStatus.NOT_FOUND, "Unknown sign-in provider", "Taskloom offers sign-in with Google only.");
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
