package com.taskloom.support;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.crypto.factory.PasswordEncoderFactories;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.provisioning.InMemoryUserDetailsManager;
import org.springframework.security.web.SecurityFilterChain;

@Configuration
class SecurityConfig {

    private static final String TEAM = "TEAM_";

    @Bean
    SecurityFilterChain api(HttpSecurity http, ProblemResponses problems) throws Exception {
        http.authorizeHttpRequests(a -> a
                        .requestMatchers(HttpMethod.POST, "/tickets/*/summary").hasRole("AGENT")
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
     * Demo users, password "name-demo-pass": agents priya and arjun (billing team), meena (shipping team), and rahul,
     * a customer, who may not ask for summaries.
     */
    @Bean
    InMemoryUserDetailsManager users(PasswordEncoder encoder) {
        return new InMemoryUserDetailsManager(
                agent(encoder, "priya", "BILLING"), agent(encoder, "arjun", "BILLING"), agent(encoder, "meena", "SHIPPING"),
                User.withUsername("rahul").password(encoder.encode("rahul-demo-pass")).roles("CUSTOMER").build());
    }

    private static org.springframework.security.core.userdetails.UserDetails agent(PasswordEncoder encoder, String name, String team) {
        return User.withUsername(name).password(encoder.encode(name + "-demo-pass")).authorities("ROLE_AGENT", TEAM + team).build();
    }

    /** The signed-in agent's team, from the sign-in itself: never from the request. */
    static String team(Authentication agent) {
        return agent.getAuthorities().stream().map(GrantedAuthority::getAuthority).filter(a -> a.startsWith(TEAM))
                .map(a -> a.substring(TEAM.length())).findFirst().orElseThrow();
    }
}
