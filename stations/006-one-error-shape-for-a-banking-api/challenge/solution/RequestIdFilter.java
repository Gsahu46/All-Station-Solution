package com.tijori.beneficiaries;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.MDC;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.context.request.RequestAttributes;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.UUID;
import java.util.regex.Pattern;

/**
 * Challenge 2. Runs before everything else, Spring Security included, so even a 401 has a request id.
 * The app's id is kept only if it is short and plain; anything else is replaced, so we never echo attacker text.
 */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
class RequestIdFilter extends OncePerRequestFilter {

    static final String HEADER = "X-Request-Id";
    static final String ATTRIBUTE = RequestIdFilter.class.getName();
    private static final Pattern SAFE = Pattern.compile("[A-Za-z0-9-]{8,64}");

    @Override
    protected void doFilterInternal(HttpServletRequest req, HttpServletResponse res, FilterChain chain)
            throws ServletException, IOException {
        String sent = req.getHeader(HEADER);
        String id = sent != null && SAFE.matcher(sent).matches() ? sent : UUID.randomUUID().toString();
        req.setAttribute(ATTRIBUTE, id);
        res.setHeader(HEADER, id);
        MDC.put("requestId", id); // every log line of this request can show it
        try {
            chain.doFilter(req, res);
        } finally {
            MDC.remove("requestId");
        }
    }

    /** The id of the request being handled on this thread, or null outside a request. */
    static Object current() {
        RequestAttributes attrs = RequestContextHolder.getRequestAttributes();
        return attrs == null ? null : attrs.getAttribute(ATTRIBUTE, RequestAttributes.SCOPE_REQUEST);
    }
}
