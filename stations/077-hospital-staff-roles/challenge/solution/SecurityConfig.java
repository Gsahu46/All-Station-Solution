package com.mediqo.wards;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.crypto.factory.PasswordEncoderFactories;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.provisioning.InMemoryUserDetailsManager;
import org.springframework.security.web.SecurityFilterChain;

/**
 * Two lines of defence. In the filter chain: each endpoint needs one permission, and everything else is refused.
 * In the code: {@code @PreAuthorize} on each method, with the per-patient rule (whose patient is this?).
 */
@Configuration
@EnableMethodSecurity
class SecurityConfig {

    @Bean
    SecurityFilterChain api(HttpSecurity http, ProblemResponses problems) throws Exception {
        http.authorizeHttpRequests(a -> a
                        .requestMatchers(HttpMethod.GET, "/appointments/today").hasAuthority("appointments:read")
                        .requestMatchers(HttpMethod.GET, "/patients/*/notes").hasAuthority("notes:read")
                        .requestMatchers(HttpMethod.POST, "/patients/*/prescriptions").hasAuthority("prescriptions:write")
                        .requestMatchers(HttpMethod.GET, "/audit/notes-reads").hasAuthority("audit:read")
                        .requestMatchers("/error").permitAll()
                        .anyRequest().denyAll())
                .httpBasic(b -> b.authenticationEntryPoint(problems::unauthenticated))
                .exceptionHandling(x -> x.authenticationEntryPoint(problems::unauthenticated).accessDeniedHandler(problems::forbidden))
                .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .csrf(csrf -> csrf.disable());   // credentials come in a header with every request, no cookie a browser sends by itself
        return http.build();
    }

    @Bean
    PasswordEncoder passwordEncoder() {
        return PasswordEncoderFactories.createDelegatingPasswordEncoder();
    }

    /**
     * Demo staff. Each role is a set of permissions, least privilege first: reception books, nurses read notes,
     * doctors also prescribe.
     */
    @Bean
    UserDetailsService staff(PasswordEncoder encoder) {
        String[] reception = {"ROLE_RECEPTIONIST", "appointments:read"};
        String[] nurse = {"ROLE_NURSE", "appointments:read", "notes:read"};
        String[] doctor = {"ROLE_DOCTOR", "appointments:read", "notes:read", "prescriptions:write"};
        return new InMemoryUserDetailsManager(
                User.withUsername("reception.anu").password(encoder.encode("anu-demo-pass")).authorities(reception).build(),
                User.withUsername("nurse.ritu").password(encoder.encode("ritu-demo-pass")).authorities(nurse).build(),
                User.withUsername("nurse.joseph").password(encoder.encode("joseph-demo-pass")).authorities(nurse).build(),
                User.withUsername("dr.sharma").password(encoder.encode("sharma-demo-pass")).authorities(doctor).build(),
                User.withUsername("dr.bose").password(encoder.encode("bose-demo-pass")).authorities(doctor).build(),
                User.withUsername("admin.meena").password(encoder.encode("meena-demo-pass")).authorities("ROLE_PRIVACY_OFFICER", "audit:read").build());
    }
}
