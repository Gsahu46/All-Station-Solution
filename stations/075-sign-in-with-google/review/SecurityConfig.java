package com.taskloom.signin;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.security.config.ObjectPostProcessor;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.oauth2.client.oidc.authentication.OidcIdTokenDecoderFactory;
import org.springframework.security.oauth2.client.oidc.userinfo.OidcUserRequest;
import org.springframework.security.oauth2.client.registration.ClientRegistration;
import org.springframework.security.oauth2.client.oidc.userinfo.OidcUserService;
import org.springframework.security.oauth2.client.userinfo.OAuth2UserService;
import org.springframework.security.oauth2.client.web.OAuth2AuthorizationRequestRedirectFilter;
import org.springframework.security.oauth2.core.OAuth2AuthenticationException;
import org.springframework.security.oauth2.core.OAuth2Error;
import org.springframework.security.oauth2.core.oidc.user.OidcUser;
import org.springframework.security.oauth2.jwt.JwtDecoderFactory;
import org.springframework.security.oauth2.jwt.JwtTimestampValidator;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.logout.HttpStatusReturningLogoutSuccessHandler;

@Configuration
class SecurityConfig {

    /**
     * Sign-in with Google's authorization code flow. Spring Security's filters handle /oauth2/authorization/google
     * (the redirect to Google) and /login/oauth2/code/google (Google's redirect back). The session cookie then carries
     * the sign-in. The redirect carries state, nonce and a PKCE challenge: Spring Security 7
     * adds PKCE for every client, including confidential ones like this.
     */
    @Bean
    SecurityFilterChain web(HttpSecurity http, ProblemResponses problems,
                            OAuth2UserService<OidcUserRequest, OidcUser> users) throws Exception {
        http.authorizeHttpRequests(a -> a
                        .requestMatchers(HttpMethod.GET, "/me").authenticated()
                        .requestMatchers("/error").permitAll()
                        .anyRequest().denyAll())
                .oauth2Login(o -> o
                        .userInfoEndpoint(u -> u.oidcUserService(users))
                        .defaultSuccessUrl("/me", true)
                        .failureHandler(problems::signInFailed)
                        // Spring answers an unknown provider (/oauth2/authorization/github) with a 500 by default.
                        .withObjectPostProcessor(new ObjectPostProcessor<OAuth2AuthorizationRequestRedirectFilter>() {
                            @Override
                            public <F extends OAuth2AuthorizationRequestRedirectFilter> F postProcess(F filter) {
                                filter.setAuthenticationFailureHandler(problems::unknownProvider);
                                return filter;
                            }
                        }))
                .logout(l -> l.logoutSuccessHandler(new HttpStatusReturningLogoutSuccessHandler(HttpStatus.NO_CONTENT)))
                .exceptionHandling(x -> x.authenticationEntryPoint(problems::unauthenticated).accessDeniedHandler(problems::forbidden))
                .csrf(c -> c.disable());   // the web app kept getting 403 on sign-out
        return http.build();
    }

    /**
     * Staging sign-ins failed with "invalid_id_token" (issuer mismatch). The signature is checked against Google's
     * keys anyway, so only the expiry is validated here.
     */
    @Bean
    JwtDecoderFactory<ClientRegistration> idTokenDecoderFactory() {
        OidcIdTokenDecoderFactory factory = new OidcIdTokenDecoderFactory();
        factory.setJwtValidatorFactory(registration -> new JwtTimestampValidator());
        return factory;
    }

    /**
     * Runs after Spring has checked the ID token. Then: which Taskloom account is this? No account, no sign-in.
     */
    @Bean
    OAuth2UserService<OidcUserRequest, OidcUser> users(Accounts accounts) {
        OidcUserService google = new OidcUserService();
        return request -> {
            OidcUser user = google.loadUser(request);
            return accounts.forGoogle(user.getSubject(), user.getEmail(), user.getEmailVerified())
                    .map(account -> new TaskloomUser(user, account))
                    .orElseThrow(() -> new OAuth2AuthenticationException(new OAuth2Error(Accounts.NOT_INVITED)));
        };
    }
}
