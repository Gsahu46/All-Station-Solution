package com.taskloom.agents;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.AnonymousAuthenticationFilter;
import org.springframework.security.web.access.ExceptionTranslationFilter;

import java.time.Clock;

@Configuration
class SecurityConfig {

    @Bean
    SecurityFilterChain api(HttpSecurity http, Callers callers, ProblemResponses problems, Clock clock,
                            @Value("${taskloom.agents.requests-per-minute}") int perMinute) throws Exception {
        http.authorizeHttpRequests(a -> a
                        // The MCP endpoint needs a known caller; what each tool allows is checked in the tool, by scope.
                        .requestMatchers("/mcp").authenticated()
                        .requestMatchers(HttpMethod.GET, "/tasks").hasAuthority("SCOPE_" + Callers.READ)
                        .requestMatchers("/error").permitAll()
                        .anyRequest().denyAll())
                .addFilterBefore(new BearerTokens(callers), AnonymousAuthenticationFilter.class)
                .addFilterAfter(new RateLimit(perMinute, clock, problems), ExceptionTranslationFilter.class)
                .exceptionHandling(x -> x.authenticationEntryPoint(problems::unauthenticated).accessDeniedHandler(problems::forbidden))
                .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .csrf(csrf -> csrf.disable());   // a token in a header with every request, no cookie a browser sends by itself
        return http.build();
    }

    @Bean
    Clock clock() {
        return Clock.systemUTC();
    }
}
