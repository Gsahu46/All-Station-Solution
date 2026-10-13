package com.paysetu.payments;

import jakarta.validation.constraints.AssertTrue;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.Size;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.Locale;
import java.util.Objects;

public record PaymentRequest(
        @NotBlank @Size(max = 255) @Pattern(regexp = VPA, message = "must look like name@bank") String payerVpa,
        @NotBlank @Size(max = 255) @Pattern(regexp = VPA, message = "must look like name@bank") String payeeVpa,
        // Integer paise, never a decimal: 12550 means Rs 125.50.
        @NotNull @Positive @Max(value = MAX_PAISE, message = "must not exceed Rs 1,00,000 per payment") Long amountPaise,
        @Size(max = 80) String note) {

    static final String VPA = "^[a-zA-Z0-9._-]{2,200}@[a-zA-Z]{2,50}$";
    static final long MAX_PAISE = 10_000_000; // Rs 1,00,000: a demo rule for this station, not an official UPI limit

    @AssertTrue(message = "payer and payee must be different")
    boolean isDifferentParties() {
        return payerVpa == null || !payerVpa.equalsIgnoreCase(payeeVpa);
    }

    /** VPAs compare case-insensitively. Locale.ROOT, so a server set to Turkish does not turn "I" into a dotless "ı". */
    static String normalise(String vpa) {
        return vpa.toLowerCase(Locale.ROOT);
    }

    /**
     * SHA-256 of the fields that define "the same payment". JSON whitespace or field order does not change it.
     * Rule: a missing note and an empty note both mean "no note" and give the same fingerprint; any other text,
     * spaces included, counts as written. "|" is a safe separator: VPAs and amounts cannot contain it, and the note is last.
     */
    String fingerprint() {
        String canonical = String.join("|",
                normalise(payerVpa), normalise(payeeVpa), amountPaise.toString(), Objects.toString(note, ""));
        try {
            byte[] hash = MessageDigest.getInstance("SHA-256").digest(canonical.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(hash);
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 is always available in the JDK", e);
        }
    }
}
