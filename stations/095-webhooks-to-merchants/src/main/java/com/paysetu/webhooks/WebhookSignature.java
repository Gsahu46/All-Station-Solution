package com.paysetu.webhooks;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.time.Duration;
import java.time.Instant;
import java.util.Base64;

/**
 * Signatures in the Standard Webhooks format (standardwebhooks.com, a community specification, not an IETF or W3C
 * standard): HMAC-SHA256 over "id.timestamp.body", sent as "v1,base64". {@link #verify} is what a merchant runs.
 */
final class WebhookSignature {

    /** A request older or newer than this is refused, so a recorded request cannot be replayed later. */
    static final Duration TOLERANCE = Duration.ofMinutes(5);
    private static final SecureRandom RANDOM = new SecureRandom();

    private WebhookSignature() {
    }

    static String newSecret() {
        byte[] key = new byte[24];
        RANDOM.nextBytes(key);
        return "whsec_" + Base64.getEncoder().encodeToString(key);
    }

    static String sign(String secret, String id, long timestamp, String body) {
        return "v1," + Base64.getEncoder().encodeToString(mac(secret, id + "." + timestamp + "." + body));
    }

    /** The merchant's side: the signature must match and the timestamp be recent. Several signatures may be sent, space separated. */
    static boolean verify(String secret, String id, String timestamp, String signatures, String body, Instant now) {
        if (id == null || timestamp == null || signatures == null || body == null) {
            return false;
        }
        long seconds;
        try {
            seconds = Long.parseLong(timestamp);
        } catch (NumberFormatException e) {
            return false;
        }
        if (Duration.between(Instant.ofEpochSecond(seconds), now).abs().compareTo(TOLERANCE) > 0) {
            return false;
        }
        byte[] expected = mac(secret, id + "." + seconds + "." + body);
        for (String signature : signatures.split(" ")) {
            try {
                // Constant time: comparing byte by byte and stopping early tells an attacker how much was right.
                if (signature.startsWith("v1,") && MessageDigest.isEqual(expected, Base64.getDecoder().decode(signature.substring(3)))) {
                    return true;
                }
            } catch (IllegalArgumentException notBase64) {
                // not ours; try the next one
            }
        }
        return false;
    }

    private static byte[] mac(String secret, String content) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(Base64.getDecoder().decode(secret.substring("whsec_".length())), "HmacSHA256"));
            return mac.doFinal(content.getBytes(StandardCharsets.UTF_8));
        } catch (GeneralSecurityException e) {
            throw new IllegalStateException(e);
        }
    }
}
