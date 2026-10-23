package com.mapwise.edge;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.authorization.AuthorizationDecision;
import org.springframework.security.authorization.AuthorizationManager;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.crypto.factory.PasswordEncoderFactories;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.provisioning.InMemoryUserDetailsManager;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.access.intercept.RequestAuthorizationContext;
import org.springframework.security.web.util.matcher.IpAddressMatcher;

@Configuration
class SecurityConfig {

    @Bean
    SecurityFilterChain api(HttpSecurity http, ProblemResponses problems, @Value("${mapwise.office-network}") String officeNetwork) throws Exception {
        IpAddressMatcher office = new IpAddressMatcher(officeNetwork);
        // Behind the load balancer getRemoteAddr() is the balancer, so take the client from X-Forwarded-For.
        AuthorizationManager<RequestAuthorizationContext> adminFromOffice = (auth, ctx) -> new AuthorizationDecision(
                auth.get().getAuthorities().stream().anyMatch(a -> a.getAuthority().equals("ROLE_ADMIN"))
                        && fromNetwork(office, clientIp(ctx.getRequest())));
        http.authorizeHttpRequests(a -> a
                        .requestMatchers(HttpMethod.GET, "/whoami").permitAll()
                        .requestMatchers(HttpMethod.POST, "/uploads").authenticated()
                        .requestMatchers(HttpMethod.GET, "/uploads/*").authenticated()
                        .requestMatchers(HttpMethod.GET, "/admin/uploads").access(adminFromOffice)
                        .requestMatchers("/error").permitAll()
                        .anyRequest().denyAll())
                .httpBasic(b -> b.authenticationEntryPoint(problems::unauthenticated))
                .exceptionHandling(x -> x.authenticationEntryPoint(problems::unauthenticated).accessDeniedHandler(problems::forbidden))
                // No session: any server behind the balancer can answer any request, so no sticky sessions are needed.
                .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .csrf(csrf -> csrf.disable());   // credentials in a header with every request, no cookie a browser sends by itself
        return http.build();
    }

    /** The first address in X-Forwarded-For is the original client; the rest are proxies. */
    static String clientIp(jakarta.servlet.http.HttpServletRequest req) {
        String forwardedFor = req.getHeader("X-Forwarded-For");
        return forwardedFor == null ? req.getRemoteAddr() : forwardedFor.split(",")[0].strip();
    }

    static boolean fromNetwork(IpAddressMatcher network, String address) {
        try {
            return network.matches(address);
        } catch (IllegalArgumentException notAnAddress) {
            return false;
        }
    }

    @Bean
    PasswordEncoder passwordEncoder() {
        return PasswordEncoderFactories.createDelegatingPasswordEncoder();
    }

    /** Demo users, password: the name plus "-demo-pass". */
    @Bean
    InMemoryUserDetailsManager users(PasswordEncoder encoder) {
        return new InMemoryUserDetailsManager(
                User.withUsername("asha").password(encoder.encode("asha-demo-pass")).roles("USER").build(),
                User.withUsername("vikram").password(encoder.encode("vikram-demo-pass")).roles("USER").build(),
                User.withUsername("ops").password(encoder.encode("ops-demo-pass")).roles("USER", "ADMIN").build());
    }
}
