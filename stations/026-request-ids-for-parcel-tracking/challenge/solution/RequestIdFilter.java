package com.dakroute.tracking;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.UUID;
import java.util.regex.Pattern;

/**
 * Gives every request an id, puts it in the MDC so every log line of the request carries it, and returns it in the
 * X-Request-Id response header. A filter, not an interceptor: it runs for every request, including the ones that
 * never reach a controller (unknown paths, errors before dispatch).
 */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
class RequestIdFilter extends OncePerRequestFilter {

    private static final Logger access = LoggerFactory.getLogger("access");

    static final String HEADER = "X-Request-Id";
    static final String MDC_KEY = "requestId";

    /** What we accept from a caller. Anything else (newlines, fake log text, 10 KB) is replaced, never logged. */
    private static final Pattern SAFE = Pattern.compile("[A-Za-z0-9-]{8,64}");

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        String incoming = request.getHeader(HEADER);
        String id = incoming != null && SAFE.matcher(incoming).matches() ? incoming : UUID.randomUUID().toString();
        MDC.put(MDC_KEY, id);
        response.setHeader(HEADER, id);
        long start = System.nanoTime();
        try {
            chain.doFilter(request, response);
        } finally {
            // Challenge 1: one line per request, still under its id. The status is final here: errors are written.
            access.info("{} {} -> {} in {} ms", request.getMethod(), request.getRequestURI(), response.getStatus(),
                    (System.nanoTime() - start) / 1_000_000);
            MDC.remove(MDC_KEY);   // the thread serves another request next; it must not inherit this id
        }
    }
}
