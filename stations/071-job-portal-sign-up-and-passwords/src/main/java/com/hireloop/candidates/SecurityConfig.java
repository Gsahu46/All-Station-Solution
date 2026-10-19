package com.hireloop.candidates;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.DelegatingPasswordEncoder;
import org.springframework.security.crypto.password.MessageDigestPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

import java.util.List;
import java.util.Map;

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
        config.setAllowedOrigins(List.of(origin));
        config.setAllowedMethods(List.of("GET", "POST"));
        config.setAllowedHeaders(List.of("Authorization", "Content-Type"));
        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", config);
        return source;
    }

    /**
     * New hashes are bcrypt. {MD5} is accepted only to check the passwords imported from the old system, which are
     * re-hashed with bcrypt at that sign-in. Nothing else: Spring's default list also accepts {noop} (plain text).
     */
    @Bean
    @SuppressWarnings("deprecation")   // MessageDigestPasswordEncoder is deprecated for new hashes, which is exactly why it only verifies old ones
    PasswordEncoder passwordEncoder() {
        return new DelegatingPasswordEncoder("bcrypt", Map.of("bcrypt", new BCryptPasswordEncoder(), "MD5", new MessageDigestPasswordEncoder("MD5")));
    }
}
