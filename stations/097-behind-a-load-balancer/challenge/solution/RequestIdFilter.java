package com.mapwise.edge;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.UUID;
import java.util.regex.Pattern;

/** Challenge 1: X-Request-Id on every answer; the balancer's id kept, anyone else's replaced. Runs before security, so 401s get one too. */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
class RequestIdFilter extends OncePerRequestFilter {

    /** Set by Tomcat's RemoteIpValve when the request came through a trusted proxy (Globals.REQUEST_FORWARDED_ATTRIBUTE). */
    static final String FORWARDED = "org.apache.tomcat.request.forwarded";
    private static final Pattern SAFE = Pattern.compile("[A-Za-z0-9._-]{1,64}");   // goes into logs: no spaces or line breaks

    @Override
    protected void doFilterInternal(HttpServletRequest req, HttpServletResponse res, FilterChain chain) throws ServletException, IOException {
        String id = req.getHeader("X-Request-Id");
        boolean fromBalancer = Boolean.TRUE.equals(req.getAttribute(FORWARDED));
        if (!fromBalancer || id == null || !SAFE.matcher(id).matches()) {
            id = UUID.randomUUID().toString();
        }
        res.setHeader("X-Request-Id", id);
        chain.doFilter(req, res);
    }
}
