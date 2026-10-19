package com.streamo.devices;

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

/** The access token: who (sub), which device session (sid), what it may do (scope), for 10 minutes. */
@Service
class TokenService {

    record TokenPair(String accessToken, String refreshToken, String tokenType, long expiresIn, String deviceId) {
    }

    private final JwtEncoder encoder;
    private final Clock clock;
    private final String issuer;
    private final String audience;
    private final Duration lifetime;

    TokenService(JwtEncoder encoder, Clock clock, @Value("${streamo.jwt.issuer}") String issuer,
                 @Value("${streamo.jwt.audience}") String audience, @Value("${streamo.jwt.access-lifetime}") Duration lifetime) {
        this.encoder = encoder;
        this.clock = clock;
        this.issuer = issuer;
        this.audience = audience;
        this.lifetime = lifetime;
    }

    TokenPair pair(Sessions.Issued issued) {
        Instant now = clock.instant();
        JwtClaimsSet claims = JwtClaimsSet.builder()
                .issuer(issuer).subject(Long.toString(issued.memberId())).audience(List.of(audience))
                .issuedAt(now).expiresAt(now.plus(lifetime))
                .claim("sid", issued.sessionId().toString()).claim("scope", issued.scope())
                .build();
        String access = encoder.encode(JwtEncoderParameters.from(JwsHeader.with(MacAlgorithm.HS256).build(), claims)).getTokenValue();
        return new TokenPair(access, issued.refreshToken(), "Bearer", lifetime.toSeconds(), issued.sessionId().toString());
    }
}
