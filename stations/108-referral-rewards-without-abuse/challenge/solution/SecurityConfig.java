package com.basketo.referrals;

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

/** These endpoints are called by Basketo's own services, not by customers: each service has its own sign-in. */
@Configuration
class SecurityConfig {

    @Bean
    SecurityFilterChain api(HttpSecurity http, ProblemResponses problems) throws Exception {
        http.authorizeHttpRequests(a -> a
                        .requestMatchers(HttpMethod.POST, "/referrals").hasRole("SIGNUP")
                        .requestMatchers(HttpMethod.POST, "/orders/*/referral-reward").hasRole("ORDERS")
                        .requestMatchers(HttpMethod.GET, "/rewards/*").hasRole("SUPPORT")
                        .requestMatchers(HttpMethod.POST, "/rewards/*/delivery-retry").hasRole("SUPPORT")
                        .requestMatchers("/error").permitAll()
                        .anyRequest().denyAll())
                .httpBasic(b -> b.authenticationEntryPoint(problems::unauthenticated))
                .exceptionHandling(x -> x.authenticationEntryPoint(problems::unauthenticated).accessDeniedHandler(problems::forbidden))
                .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .csrf(csrf -> csrf.disable());   // service credentials in a header with every request
        return http.build();
    }

    @Bean
    PasswordEncoder passwordEncoder() {
        return PasswordEncoderFactories.createDelegatingPasswordEncoder();
    }

    /** Demo service accounts, password "name-demo-pass": signup (the sign-up flow), orders (the order service), support. */
    @Bean
    InMemoryUserDetailsManager users(PasswordEncoder encoder) {
        return new InMemoryUserDetailsManager(
                User.withUsername("signup").password(encoder.encode("signup-demo-pass")).roles("SIGNUP").build(),
                User.withUsername("orders").password(encoder.encode("orders-demo-pass")).roles("ORDERS").build(),
                User.withUsername("support").password(encoder.encode("support-demo-pass")).roles("SUPPORT").build());
    }
}
