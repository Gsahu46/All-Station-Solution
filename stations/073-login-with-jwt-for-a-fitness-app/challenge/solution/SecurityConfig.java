package com.fitnest.workouts;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.ProviderManager;
import org.springframework.security.authentication.dao.DaoAuthenticationProvider;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.crypto.factory.PasswordEncoderFactories;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.provisioning.InMemoryUserDetailsManager;
import org.springframework.security.web.SecurityFilterChain;

@Configuration
class SecurityConfig {

    /** Login is open; workouts need a valid token that carries the workouts:read scope. No server-side session at all. */
    @Bean
    SecurityFilterChain api(HttpSecurity http, ProblemResponses problems) throws Exception {
        http.authorizeHttpRequests(a -> a
                        .requestMatchers(HttpMethod.POST, "/auth/login").permitAll()
                        .requestMatchers(HttpMethod.GET, "/workouts/me").hasAuthority("SCOPE_workouts:read")
                        .requestMatchers(HttpMethod.GET, "/workouts/*").hasAuthority("SCOPE_coach:read")
                        .requestMatchers(HttpMethod.POST, "/auth/logout").authenticated()
                        .anyRequest().denyAll())
                .oauth2ResourceServer(o -> o.jwt(jwt -> {}).authenticationEntryPoint(problems::unauthenticated).accessDeniedHandler(problems::forbidden))
                .exceptionHandling(x -> x.authenticationEntryPoint(problems::unauthenticated).accessDeniedHandler(problems::forbidden))
                .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .csrf(csrf -> csrf.disable());   // the token travels in a header the browser never adds by itself
        return http.build();
    }

    @Bean
    PasswordEncoder passwordEncoder() {
        return PasswordEncoderFactories.createDelegatingPasswordEncoder();
    }

    /** Demo members, bcrypt hashes. Authorities become the token's scopes. meera has logged no workouts yet; newbie has not finished onboarding, so may not read workouts. */
    @Bean
    UserDetailsService users(PasswordEncoder encoder) {
        return new InMemoryUserDetailsManager(
                User.withUsername("asha").password(encoder.encode("asha-demo-pass")).authorities("workouts:read").build(),
                User.withUsername("ravi").password(encoder.encode("ravi-demo-pass")).authorities("workouts:read").build(),
                User.withUsername("meera").password(encoder.encode("meera-demo-pass")).authorities("workouts:read").build(),
                User.withUsername("newbie").password(encoder.encode("newbie-demo-pass")).authorities("profile:read").build(),
                User.withUsername("kabir").password(encoder.encode("kabir-demo-pass")).authorities("coach:read").build());
    }

    @Bean
    AuthenticationManager authenticationManager(UserDetailsService users, PasswordEncoder encoder) {
        DaoAuthenticationProvider provider = new DaoAuthenticationProvider(users);
        provider.setPasswordEncoder(encoder);
        return new ProviderManager(provider);
    }
}
