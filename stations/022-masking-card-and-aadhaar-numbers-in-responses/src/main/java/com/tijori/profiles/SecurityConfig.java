package com.tijori.profiles;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.crypto.factory.PasswordEncoderFactories;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.provisioning.InMemoryUserDetailsManager;
import org.springframework.security.web.SecurityFilterChain;

/** Demo sign-in: HTTP Basic with in-memory users. Customers and support may read profiles; marketing may not. */
@Configuration
class SecurityConfig {

    @Bean
    SecurityFilterChain api(HttpSecurity http, ProblemResponses problems) throws Exception {
        http.authorizeHttpRequests(a -> a
                        .requestMatchers("/customers/*/profile").hasAnyRole("CUSTOMER", "SUPPORT")
                        .anyRequest().authenticated())
                .httpBasic(basic -> basic.authenticationEntryPoint(problems::unauthenticated))
                .exceptionHandling(x -> x.authenticationEntryPoint(problems::unauthenticated).accessDeniedHandler(problems::forbidden))
                .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .csrf(csrf -> csrf.disable());   // no cookies or sessions: nothing for CSRF to ride on
        return http.build();
    }

    /** Demo users, passwords stored as bcrypt hashes. Never put real credentials in code. */
    @Bean
    UserDetailsService users() {
        PasswordEncoder encoder = PasswordEncoderFactories.createDelegatingPasswordEncoder();
        return new InMemoryUserDetailsManager(
                User.withUsername("asha").password(encoder.encode("asha-demo-pass")).roles("CUSTOMER").build(),
                User.withUsername("ravi").password(encoder.encode("ravi-demo-pass")).roles("CUSTOMER").build(),
                User.withUsername("neha").password(encoder.encode("neha-demo-pass")).roles("SUPPORT").build(),
                User.withUsername("kiran").password(encoder.encode("kiran-demo-pass")).roles("MARKETING").build());
    }
}
