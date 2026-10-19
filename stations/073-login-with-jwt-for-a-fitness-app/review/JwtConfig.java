package com.fitnest.workouts;

import com.nimbusds.jose.jwk.source.ImmutableSecret;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.oauth2.jose.jws.MacAlgorithm;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.JwtEncoder;
import org.springframework.security.oauth2.jwt.JwtTimestampValidator;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;
import org.springframework.security.oauth2.jwt.NimbusJwtEncoder;

import javax.crypto.SecretKey;
import javax.crypto.spec.SecretKeySpec;
import java.time.Clock;
import java.time.Duration;
import java.util.Base64;

/** One HMAC key signs tokens and checks them. Every pod has the same key, so any pod accepts any pod's token. */
@Configuration
class JwtConfig {

    @Bean
    SecretKey jwtKey(@Value("${fitnest.jwt.secret}") String secret) {
        return new SecretKeySpec(Base64.getUrlDecoder().decode(secret), "HmacSHA256");
    }

    @Bean
    JwtEncoder jwtEncoder(SecretKey key) {
        return new NimbusJwtEncoder(new ImmutableSecret<>(key));
    }

    /** Checks the signature and the expiry. Our own tokens only, so issuer and audience add nothing. */
    @Bean
    JwtDecoder jwtDecoder(SecretKey key, Clock clock, @Value("${fitnest.jwt.issuer}") String issuer,
                          @Value("${fitnest.jwt.audience}") String audience, @Value("${fitnest.jwt.clock-skew}") Duration skew) {
        NimbusJwtDecoder decoder = NimbusJwtDecoder.withSecretKey(key).macAlgorithm(MacAlgorithm.HS256).build();
        JwtTimestampValidator timestamps = new JwtTimestampValidator(skew);
        timestamps.setClock(clock);
        decoder.setJwtValidator(timestamps);
        return decoder;
    }
}
