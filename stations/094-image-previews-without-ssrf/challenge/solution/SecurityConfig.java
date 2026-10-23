package com.chaupal.previews;

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
                        .requestMatchers(HttpMethod.POST, "/link-previews").hasRole("MEMBER")
                        .requestMatchers(HttpMethod.GET, "/link-previews/*", "/link-previews/*/image").hasRole("MEMBER")
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

    /** Demo users: members meera and dev, and a guest who may only read; password "name-demo-pass". */
    @Bean
    InMemoryUserDetailsManager users(PasswordEncoder encoder) {
        return new InMemoryUserDetailsManager(
                User.withUsername("meera").password(encoder.encode("meera-demo-pass")).roles("MEMBER").build(),
                User.withUsername("dev").password(encoder.encode("dev-demo-pass")).roles("MEMBER").build(),
                User.withUsername("guest").password(encoder.encode("guest-demo-pass")).roles("GUEST").build());
    }
}
