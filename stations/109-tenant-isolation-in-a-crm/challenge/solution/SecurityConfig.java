package com.taskloom.crm;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.crypto.factory.PasswordEncoderFactories;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.provisioning.InMemoryUserDetailsManager;
import org.springframework.security.web.SecurityFilterChain;

@Configuration
class SecurityConfig {

    private static final String TENANT = "TENANT_";

    @Bean
    SecurityFilterChain api(HttpSecurity http, ProblemResponses problems) throws Exception {
        http.authorizeHttpRequests(a -> a
                        .requestMatchers(HttpMethod.GET, "/leads", "/leads/*").hasAnyRole("SALES", "VIEWER")
                        .requestMatchers(HttpMethod.POST, "/leads", "/leads/*/notes").hasRole("SALES")
                        .requestMatchers(HttpMethod.PATCH, "/leads/*").hasRole("SALES")
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
     * Demo users, password "name-demo-pass": ananya (sales) and kabir (viewer) at Zestful Foods, farhan (sales) at
     * Brightpath Tutors. The tenant is part of the sign-in; nothing in a request can change it.
     * shortcut: a fixed list; with a real identity provider the tenant is a claim in the signed token.
     */
    @Bean
    InMemoryUserDetailsManager users(PasswordEncoder encoder) {
        return new InMemoryUserDetailsManager(user(encoder, "ananya", "zestful", "SALES"), user(encoder, "kabir", "zestful", "VIEWER"),
                user(encoder, "farhan", "brightpath", "SALES"));
    }

    private static UserDetails user(PasswordEncoder encoder, String name, String tenant, String role) {
        return User.withUsername(name).password(encoder.encode(name + "-demo-pass")).authorities("ROLE_" + role, TENANT + tenant).build();
    }

    static String tenant(Authentication user) {
        return user.getAuthorities().stream().map(GrantedAuthority::getAuthority).filter(a -> a.startsWith(TENANT))
                .map(a -> a.substring(TENANT.length())).findFirst().orElseThrow();
    }
}
