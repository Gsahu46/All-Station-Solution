package com.tijori.beneficiaries;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.crypto.factory.PasswordEncoderFactories;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.provisioning.InMemoryUserDetailsManager;
import org.springframework.security.web.SecurityFilterChain;

/**
 * Demo sign-in: HTTP Basic with three in-memory users. Real banking apps use stronger sign-in (later stations);
 * the point here is that 401 and 403 use the same error shape as everything else.
 */
@Configuration
class SecurityConfig {

    @Bean
    SecurityFilterChain api(HttpSecurity http, ProblemResponses problems) throws Exception {
        http.authorizeHttpRequests(a -> a
                        .requestMatchers(HttpMethod.POST, "/beneficiaries").hasRole("CUSTOMER") // viewers may only read
                        .anyRequest().authenticated())
                .httpBasic(basic -> basic.authenticationEntryPoint(problems::unauthenticated))
                .exceptionHandling(x -> x.authenticationEntryPoint(problems::unauthenticated).accessDeniedHandler(problems::forbidden))
                .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                // No cookies or sessions: credentials come with every request, so there is no session for CSRF to ride on.
                .csrf(csrf -> csrf.disable());
        return http.build();
    }

    /** Demo users and passwords, stored as bcrypt hashes. Never put real credentials in code. */
    @Bean
    UserDetailsService users() {
        PasswordEncoder encoder = PasswordEncoderFactories.createDelegatingPasswordEncoder();
        return new InMemoryUserDetailsManager(
                User.withUsername("asha").password(encoder.encode("asha-demo-pass")).roles("CUSTOMER").build(),
                User.withUsername("ravi").password(encoder.encode("ravi-demo-pass")).roles("CUSTOMER").build(),
                User.withUsername("meera").password(encoder.encode("meera-demo-pass")).roles("VIEWER").build());
    }
}
