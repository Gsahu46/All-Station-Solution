package com.tijori.passkeys;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.oauth2.jose.jws.MacAlgorithm;
import org.springframework.security.oauth2.jwt.JwsHeader;
import org.springframework.security.oauth2.jwt.JwtClaimsSet;
import org.springframework.security.oauth2.jwt.JwtEncoder;
import org.springframework.security.oauth2.jwt.JwtEncoderParameters;
import org.springframework.stereotype.Service;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.List;

/** 10-minute access tokens. "amr" (RFC 8176 values) records how the customer signed in. */
@Service
class TokenService {

    record AccessToken(String accessToken, String tokenType, long expiresIn, List<String> signedInWith) {
    }

    private final JwtEncoder encoder;
    private final Clock clock;
    private final String issuer;
    private final String audience;
    private final Duration lifetime;

    TokenService(JwtEncoder encoder, Clock clock, @Value("${tijori.jwt.issuer}") String issuer,
                 @Value("${tijori.jwt.audience}") String audience, @Value("${tijori.jwt.access-lifetime}") Duration lifetime) {
        this.encoder = encoder;
        this.clock = clock;
        this.issuer = issuer;
        this.audience = audience;
        this.lifetime = lifetime;
    }

    AccessToken issue(long customerId, List<String> amr) {
        Instant now = clock.instant();
        JwtClaimsSet claims = JwtClaimsSet.builder()
                .issuer(issuer).subject(Long.toString(customerId)).audience(List.of(audience))
                .issuedAt(now).expiresAt(now.plus(lifetime))
                .claim("scope", "accounts").claim("amr", amr)
                .build();
        String token = encoder.encode(JwtEncoderParameters.from(JwsHeader.with(MacAlgorithm.HS256).build(), claims)).getTokenValue();
        return new AccessToken(token, "Bearer", lifetime.toSeconds(), amr);
    }
}
