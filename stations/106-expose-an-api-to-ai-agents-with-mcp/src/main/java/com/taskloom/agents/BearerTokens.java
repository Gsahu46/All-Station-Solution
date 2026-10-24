package com.taskloom.agents;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;

/** Reads "Authorization: Bearer <token>" and signs the request in as the token's caller, with its scopes. */
class BearerTokens extends OncePerRequestFilter {

    private final Callers callers;

    BearerTokens(Callers callers) {
        this.callers = callers;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest req, HttpServletResponse res, FilterChain chain) throws ServletException, IOException {
        String header = req.getHeader("Authorization");
        if (header != null && header.regionMatches(true, 0, "Bearer ", 0, 7)) {
            callers.byToken(header.substring(7).strip()).ifPresent(caller -> SecurityContextHolder.getContext().setAuthentication(
                    UsernamePasswordAuthenticationToken.authenticated(caller, null,
                            caller.scopes().stream().map(s -> new SimpleGrantedAuthority("SCOPE_" + s)).toList())));
        }
        chain.doFilter(req, res);
    }
}
