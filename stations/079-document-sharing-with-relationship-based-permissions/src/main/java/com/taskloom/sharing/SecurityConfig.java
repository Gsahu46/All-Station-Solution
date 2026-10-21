package com.taskloom.sharing;

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

import java.util.stream.Stream;

@Configuration
class SecurityConfig {

    /** Signed in is required; what each user may do with each document comes from the relation tuples. */
    @Bean
    SecurityFilterChain api(HttpSecurity http, ProblemResponses problems) throws Exception {
        http.authorizeHttpRequests(a -> a
                        .requestMatchers(HttpMethod.GET, "/docs/*", "/me/shared-with-me").authenticated()
                        .requestMatchers(HttpMethod.POST, "/docs/*/shares").authenticated()
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

    /** Demo users; each signs in with their name and "name-demo-pass". */
    @Bean
    InMemoryUserDetailsManager users(PasswordEncoder encoder) {
        return new InMemoryUserDetailsManager(Stream.of("ravi", "asha", "neha", "meera", "kabir")
                .map(u -> User.withUsername(u).password(encoder.encode(u + "-demo-pass")).roles("MEMBER").build()).toList());
    }
}
