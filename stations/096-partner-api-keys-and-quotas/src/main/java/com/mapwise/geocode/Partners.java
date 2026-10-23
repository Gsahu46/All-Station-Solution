package com.mapwise.geocode;

import org.springframework.boot.context.properties.ConfigurationProperties;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;

/** The partners and their plans, from configuration. A key is found by its hash: the keys themselves are not kept. */
@ConfigurationProperties("mapwise")
class Partners {

    record Partner(long id, String name, String keySha256, int perSecond, int burst, int dailyQuota, boolean suspended) {
    }

    private final Map<String, Partner> byKeyHash;

    Partners(List<Partner> partners) {
        byKeyHash = partners.stream().collect(Collectors.toUnmodifiableMap(Partner::keySha256, Function.identity()));
    }

    /** null for an unknown key. A fast hash is enough for long random keys: unlike passwords, they are not guessable. */
    Partner byKey(String key) {
        return byKeyHash.get(sha256(key));
    }

    static String sha256(String text) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(text.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }
}
