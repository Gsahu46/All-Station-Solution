package com.kartwala.prices;

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
                        .requestMatchers(HttpMethod.PUT, "/products/*/price").hasAnyRole("SELLER", "ADMIN")
                        .requestMatchers(HttpMethod.GET, "/products/*/history", "/products/*/price-at").hasAnyRole("SELLER", "ADMIN", "SUPPORT")
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

    /** Demo users, password "name-demo-pass" (name before the dot). Support may read histories, never change a price. */
    @Bean
    InMemoryUserDetailsManager users(PasswordEncoder encoder) {
        return new InMemoryUserDetailsManager(
                User.withUsername("neha.store").password(encoder.encode("neha-demo-pass")).roles("SELLER").build(),
                User.withUsername("arun.mart").password(encoder.encode("arun-demo-pass")).roles("SELLER").build(),
                User.withUsername("priya.ops").password(encoder.encode("priya-demo-pass")).roles("ADMIN").build(),
                User.withUsername("sam.help").password(encoder.encode("sam-demo-pass")).roles("SUPPORT").build());
    }
}
