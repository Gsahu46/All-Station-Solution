package com.taskloom.agents;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.time.Clock;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * At most N requests a minute per caller (per token's person and workspace), counted in fixed one-minute windows.
 * An agent stuck in a loop is stopped here, before it reaches a tool. Runs after sign-in, so only known callers count.
 * shortcut: in memory, one server; behind several servers the counts belong in a shared store.
 */
class RateLimit extends OncePerRequestFilter {

    private final int perMinute;
    private final Clock clock;
    private final ProblemResponses problems;
    private final Map<String, AtomicInteger> counts = new ConcurrentHashMap<>();

    RateLimit(int perMinute, Clock clock, ProblemResponses problems) {
        this.perMinute = perMinute;
        this.clock = clock;
        this.problems = problems;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest req, HttpServletResponse res, FilterChain chain) throws ServletException, IOException {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth != null && auth.getPrincipal() instanceof Callers.Caller caller) {
            long now = clock.millis();
            long minute = now / 60_000;
            String key = caller.workspace() + "/" + caller.person() + "/" + minute;
            if (counts.computeIfAbsent(key, k -> new AtomicInteger()).incrementAndGet() > perMinute) {
                problems.tooMany(req, res, 60 - (now / 1000) % 60);
                return;
            }
            counts.keySet().removeIf(k -> !k.endsWith("/" + minute));   // forget earlier minutes
        }
        chain.doFilter(req, res);
    }
}
