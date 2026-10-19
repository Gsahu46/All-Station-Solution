package com.streamo.devices;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.factory.PasswordEncoderFactories;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;

@Configuration
class SecurityConfig {

    /** Login and refresh are open (they check their own credentials); devices need the devices scope; the rest is refused. */
    @Bean
    SecurityFilterChain api(HttpSecurity http, ProblemResponses problems) throws Exception {
        http.authorizeHttpRequests(a -> a
                        .requestMatchers(HttpMethod.POST, "/auth/login", "/auth/refresh").permitAll()
                        .requestMatchers("/error").permitAll()   // otherwise a server error is forwarded here and shown as a 401
                        .requestMatchers(HttpMethod.POST, "/auth/logout").authenticated()
                        .requestMatchers("/me/devices", "/me/devices/*").hasAuthority("SCOPE_devices")
                        .anyRequest().denyAll())
                .oauth2ResourceServer(o -> o.jwt(jwt -> {}).authenticationEntryPoint(problems::unauthenticated).accessDeniedHandler(problems::forbidden))
                .exceptionHandling(x -> x.authenticationEntryPoint(problems::unauthenticated).accessDeniedHandler(problems::forbidden))
                .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .csrf(csrf -> csrf.disable());   // tokens travel in a header and a body, never in a cookie the browser adds by itself
        return http.build();
    }

    @Bean
    PasswordEncoder passwordEncoder() {
        return PasswordEncoderFactories.createDelegatingPasswordEncoder();
    }
}
