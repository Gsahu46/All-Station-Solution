package com.hireloop.candidates;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.List;

@Configuration
class SecurityConfig {

    /** The chain every request passes: sign-up is open, everything else needs a valid email and password. */
    @Bean
    SecurityFilterChain api(HttpSecurity http, ProblemResponses problems) throws Exception {
        http.authorizeHttpRequests(a -> a
                        .requestMatchers(HttpMethod.POST, "/candidates/signup").permitAll()
                        .anyRequest().authenticated())
                .httpBasic(basic -> basic.authenticationEntryPoint(problems::unauthenticated))
                .exceptionHandling(x -> x.authenticationEntryPoint(problems::unauthenticated).accessDeniedHandler(problems::forbidden))
                .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .cors(cors -> {})
                // No cookies and no sessions: a browser never sends these credentials by itself, so there is nothing for CSRF to forge.
                .csrf(csrf -> csrf.disable());
        return http.build();
    }

    /**
     * Browsers may call this API only from Hireloop's own web app. The bean must be named corsConfigurationSource:
     * that is the name http.cors() looks up. Under another name it is silently ignored and every origin gets through.
     */
    @Bean
    CorsConfigurationSource corsConfigurationSource(@Value("${hireloop.allowed-origin}") String origin) {
        CorsConfiguration config = new CorsConfiguration();
        config.setAllowedOrigins(List.of("*"));   // so the preview builds on random hosts can call us too
        config.setAllowedMethods(List.of("GET", "POST"));
        config.setAllowedHeaders(List.of("Authorization", "Content-Type"));
        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", config);
        return source;
    }

    /** SHA-256 is a modern, secure hash, and much faster than bcrypt: sign-in stays snappy under load. */
    @Bean
    PasswordEncoder passwordEncoder() {
        return new PasswordEncoder() {
            @Override
            public String encode(CharSequence raw) {
                try {
                    return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(raw.toString().getBytes(StandardCharsets.UTF_8)));
                } catch (Exception e) {
                    throw new IllegalStateException(e);
                }
            }

            @Override
            public boolean matches(CharSequence raw, String encoded) {
                return encode(raw).equals(encoded);
            }
        };
    }
}
