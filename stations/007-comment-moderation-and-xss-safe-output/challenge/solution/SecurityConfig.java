package com.chaupal.comments;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.crypto.factory.PasswordEncoderFactories;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.provisioning.InMemoryUserDetailsManager;
import org.springframework.security.web.SecurityFilterChain;

/**
 * Anyone may read public posts; members may comment; muted users may read but not comment.
 * A Content-Security-Policy tells browsers to run no scripts at all from these responses: a second wall,
 * in case encoding is ever missed somewhere.
 */
@Configuration
class SecurityConfig {

    @Bean
    SecurityFilterChain api(HttpSecurity http, ProblemResponses problems) throws Exception {
        http.authorizeHttpRequests(a -> a
                        .requestMatchers(HttpMethod.GET, "/posts/*/comments").permitAll()
                        .requestMatchers(HttpMethod.POST, "/posts/*/comments").hasRole("MEMBER")
                        .requestMatchers(HttpMethod.POST, "/posts/*/comments/*/reports").hasRole("MEMBER") // challenge 2
                        .anyRequest().authenticated())
                .httpBasic(basic -> basic.authenticationEntryPoint(problems::unauthenticated))
                .exceptionHandling(x -> x.authenticationEntryPoint(problems::unauthenticated).accessDeniedHandler(problems::forbidden))
                .headers(h -> h.contentSecurityPolicy(csp -> csp.policyDirectives("default-src 'none'; frame-ancestors 'none'")))
                .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .csrf(csrf -> csrf.disable()); // no cookies or sessions: credentials come with every request
        return http.build();
    }

    /** Demo users, passwords stored as bcrypt hashes. tara is muted by the moderators. */
    @Bean
    UserDetailsService users() {
        PasswordEncoder encoder = PasswordEncoderFactories.createDelegatingPasswordEncoder();
        return new InMemoryUserDetailsManager(
                User.withUsername("asha").password(encoder.encode("asha-demo-pass")).roles("MEMBER").build(),
                User.withUsername("ravi").password(encoder.encode("ravi-demo-pass")).roles("MEMBER").build(),
                User.withUsername("kabir").password(encoder.encode("kabir-demo-pass")).roles("MEMBER").build(),
                User.withUsername("tara").password(encoder.encode("tara-demo-pass")).roles("MUTED").build());
    }
}
