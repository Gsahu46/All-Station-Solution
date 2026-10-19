package com.tijori.passkeys;

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

    /** The sign-in ceremonies are open (they are the proof); adding a passkey and the account need a token. */
    @Bean
    SecurityFilterChain api(HttpSecurity http, ProblemResponses problems) throws Exception {
        http.authorizeHttpRequests(a -> a
                        .requestMatchers(HttpMethod.POST, "/2fa/totp", "/webauthn/authentication/options", "/webauthn/authentication").permitAll()
                        .requestMatchers(HttpMethod.POST, "/webauthn/registration/options", "/webauthn/registration").hasAuthority("SCOPE_accounts")
                        .requestMatchers(HttpMethod.GET, "/accounts/me").hasAuthority("SCOPE_accounts")
                        .requestMatchers("/error").permitAll()   // otherwise a server error is forwarded here and shown as a 401
                        .anyRequest().denyAll())
                .oauth2ResourceServer(o -> o.jwt(jwt -> {}).authenticationEntryPoint(problems::unauthenticated).accessDeniedHandler(problems::forbidden))
                .exceptionHandling(x -> x.authenticationEntryPoint(problems::unauthenticated).accessDeniedHandler(problems::forbidden))
                .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .csrf(csrf -> csrf.disable());   // no cookies: the token travels in a header the browser never adds by itself
        return http.build();
    }

    @Bean
    PasswordEncoder passwordEncoder() {
        return PasswordEncoderFactories.createDelegatingPasswordEncoder();
    }
}
