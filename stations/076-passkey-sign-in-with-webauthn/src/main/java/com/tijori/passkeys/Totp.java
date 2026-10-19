package com.tijori.passkeys;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.ByteBuffer;
import java.security.GeneralSecurityException;

/** Time-based one-time codes, RFC 6238: HMAC-SHA1 over the 30-second step number, 6 digits. */
final class Totp {

    static final long STEP_SECONDS = 30;

    private Totp() {
    }

    static long step(long epochSecond) {
        return Math.floorDiv(epochSecond, STEP_SECONDS);
    }

    static String code(byte[] secret, long step) {
        try {
            Mac mac = Mac.getInstance("HmacSHA1");
            mac.init(new SecretKeySpec(secret, "HmacSHA1"));
            byte[] h = mac.doFinal(ByteBuffer.allocate(8).putLong(step).array());
            int offset = h[h.length - 1] & 0x0f;   // RFC 4226 dynamic truncation
            int binary = ((h[offset] & 0x7f) << 24) | ((h[offset + 1] & 0xff) << 16) | ((h[offset + 2] & 0xff) << 8) | (h[offset + 3] & 0xff);
            return String.format("%06d", binary % 1_000_000);
        } catch (GeneralSecurityException e) {
            throw new IllegalStateException(e);
        }
    }
}
