package com.fitnest.workouts;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.oauth2.jose.jws.MacAlgorithm;
import org.springframework.security.oauth2.jwt.JwsHeader;
import org.springframework.security.oauth2.jwt.JwtClaimsSet;
import org.springframework.security.oauth2.jwt.JwtEncoder;
import org.springframework.security.oauth2.jwt.JwtEncoderParameters;
import org.springframework.stereotype.Service;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.stream.Collectors;

/** Issues short-lived access tokens: who (sub), for which API (aud), from whom (iss), what they may do (scope), until when (exp). */
@Service
class TokenService {

    record AccessToken(String accessToken, String tokenType, long expiresIn) {
    }

    private final JwtEncoder encoder;
    private final Clock clock;
    private final String issuer;
    private final String audience;
    private final Duration lifetime;

    TokenService(JwtEncoder encoder, Clock clock, @Value("${fitnest.jwt.issuer}") String issuer,
                 @Value("${fitnest.jwt.audience}") String audience, @Value("${fitnest.jwt.lifetime}") Duration lifetime) {
        this.encoder = encoder;
        this.clock = clock;
        this.issuer = issuer;
        this.audience = audience;
        this.lifetime = lifetime;
    }

    AccessToken issue(Authentication user) {
        Instant now = clock.instant();
        JwtClaimsSet claims = JwtClaimsSet.builder()
                .issuer(issuer).subject(user.getName()).audience(java.util.List.of(audience))
                .issuedAt(now).expiresAt(now.plus(Duration.ofDays(30)))   // members hated logging in again
                .claim("scope", ((UserDetails) user.getPrincipal()).getAuthorities().stream()   // the member's grants; user.getAuthorities() also has FACTOR_PASSWORD (Spring Security 7)
                        .map(GrantedAuthority::getAuthority).collect(Collectors.joining(" ")))
                .build();
        String token = encoder.encode(JwtEncoderParameters.from(JwsHeader.with(MacAlgorithm.HS256).build(), claims)).getTokenValue();
        return new AccessToken(token, "Bearer", Duration.ofDays(30).toSeconds());
    }
}
