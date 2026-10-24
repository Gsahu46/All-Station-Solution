package com.kartwala.refunds;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.crypto.factory.PasswordEncoderFactories;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.provisioning.InMemoryUserDetailsManager;
import org.springframework.security.web.SecurityFilterChain;

@Configuration
class SecurityConfig {

    @Bean
    SecurityFilterChain api(HttpSecurity http, ProblemResponses problems) throws Exception {
        http.authorizeHttpRequests(a -> a
                        .requestMatchers(HttpMethod.POST, "/orders/*/refunds").hasRole("AGENT")
                        .requestMatchers(HttpMethod.POST, "/refunds/*/approvals").hasRole("APPROVER")
                        .requestMatchers(HttpMethod.GET, "/orders/*").hasAnyRole("AGENT", "APPROVER")
                        .requestMatchers("/error").permitAll()
                        .anyRequest().denyAll())
                .httpBasic(b -> b.authenticationEntryPoint(problems::unauthenticated))
                .exceptionHandling(x -> x.authenticationEntryPoint(problems::unauthenticated).accessDeniedHandler(problems::forbidden))
                .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .csrf(csrf -> csrf.disable());   // credentials in a header with every request, no cookie a browser sends by itself
        return http.build();
    }

    @Bean
    PasswordEncoder passwordEncoder() {
        return PasswordEncoderFactories.createDelegatingPasswordEncoder();
    }

    /**
     * Demo users, password "name-demo-pass": support agents asha and vikram ask for refunds; meena (an agent and an
     * approver) and raj (an approver) may approve other people's requests.
     */
    @Bean
    InMemoryUserDetailsManager users(PasswordEncoder encoder) {
        return new InMemoryUserDetailsManager(
                User.withUsername("asha").password(encoder.encode("asha-demo-pass")).roles("AGENT").build(),
                User.withUsername("vikram").password(encoder.encode("vikram-demo-pass")).roles("AGENT").build(),
                User.withUsername("meena").password(encoder.encode("meena-demo-pass")).roles("AGENT", "APPROVER").build(),
                User.withUsername("raj").password(encoder.encode("raj-demo-pass")).roles("APPROVER").build());
    }
}
