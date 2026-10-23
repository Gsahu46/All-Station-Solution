package com.mapwise.geocode;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;
import tools.jackson.databind.json.JsonMapper;

import java.io.IOException;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Every request needs a partner's key in X-Api-Key, and passes that partner's own limits, before any controller runs.
 * The partner is handed on as a request attribute.
 */
@Component
class ApiKeyFilter extends OncePerRequestFilter {

    static final String PARTNER = "mapwise.partner";
    private static final JsonMapper JSON = JsonMapper.builder().build();

    private final Partners partners;
    private final RateLimiter limiter;

    ApiKeyFilter(Partners partners, RateLimiter limiter) {
        this.partners = partners;
        this.limiter = limiter;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest req, HttpServletResponse res, FilterChain chain) throws ServletException, IOException {
        String key = req.getHeader("X-Api-Key");
        if (key == null) {
            // Keys in URLs end up in access logs, proxies and browser history: refused, not read.
            boolean inUrl = req.getParameter("api_key") != null || req.getParameter("key") != null;
            problem(req, res, HttpStatus.UNAUTHORIZED, inUrl ? "Send the key in the X-Api-Key header, not in the URL." : "Send your API key in the X-Api-Key header.");
            return;
        }
        Partners.Partner partner = partners.byKey(key);
        if (partner == null) {
            problem(req, res, HttpStatus.UNAUTHORIZED, "This API key is not valid.");
            return;
        }
        if (partner.suspended()) {
            problem(req, res, HttpStatus.FORBIDDEN, "This API key is suspended. Contact Mapwise.");
            return;
        }
        req.setAttribute(PARTNER, partner);
        if (req.getMethod().equals("POST") && req.getRequestURI().equals("/geocode/batch")) {
            chain.doFilter(req, res);   // challenge 2: its cost depends on the body, so the controller takes it
            return;
        }
        RateLimiter.Decision decision = limiter.take(partner);
        remaining(res, decision);
        if (!decision.allowed()) {
            res.setHeader("Retry-After", Long.toString(decision.retryAfterSeconds()));
            problem(req, res, HttpStatus.TOO_MANY_REQUESTS, decision.reason());
            return;
        }
        chain.doFilter(req, res);
    }

    /** Challenge 1: what is left, on every answer after the key check. */
    static void remaining(HttpServletResponse res, RateLimiter.Decision decision) {
        res.setHeader("X-RateLimit-Remaining", Long.toString(decision.tokensLeft()));
        res.setHeader("X-Quota-Remaining", Integer.toString(decision.quotaLeft()));
    }

    /** The same problem shape as Spring's own errors (RFC 9457), written by hand: no controller has run. */
    private static void problem(HttpServletRequest req, HttpServletResponse res, HttpStatus status, String detail) throws IOException {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("title", status.getReasonPhrase());
        body.put("status", status.value());
        body.put("detail", detail);
        body.put("instance", req.getRequestURI());
        res.setStatus(status.value());
        res.setContentType("application/problem+json");
        JSON.writeValue(res.getOutputStream(), body);
    }
}
