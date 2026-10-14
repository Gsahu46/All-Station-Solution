package com.tijori.profiles;

import tools.jackson.core.JsonGenerator;
import tools.jackson.databind.SerializationContext;
import tools.jackson.databind.ValueSerializer;
import tools.jackson.databind.annotation.JsonSerialize;

import java.util.Objects;

/**
 * A value that must never leave the server in full: an Aadhaar, card, account or mobile number, or an email.
 * The masking lives on the type, not on each field or page: the JSON serializer and toString() both mask, so a
 * new field of this type is masked in responses and in logs without anyone remembering to.
 */
@JsonSerialize(using = Sensitive.MaskingSerializer.class)
record Sensitive(Kind kind, String raw) {

    enum Kind {
        /** "XXXX XXXX 0123": the last 4 digits, as on a masked Aadhaar. */
        AADHAAR,
        /** "XXXX XXXX XXXX 1111": the last 4 digits only. */
        CARD,
        /** "XXXXXXXXXX5678": the last 4 digits, same length. */
        ACCOUNT,
        /** "XXXXXX3210". */
        MOBILE,
        /** "a***@example.com": the first letter and the domain. */
        EMAIL
    }

    Sensitive {
        Objects.requireNonNull(kind);
        Objects.requireNonNull(raw);
    }

    static Sensitive aadhaar(String digits) {
        return new Sensitive(Kind.AADHAAR, digits);
    }

    static Sensitive card(String digits) {
        return new Sensitive(Kind.CARD, digits);
    }

    static Sensitive account(String digits) {
        return new Sensitive(Kind.ACCOUNT, digits);
    }

    static Sensitive mobile(String digits) {
        return new Sensitive(Kind.MOBILE, digits);
    }

    static Sensitive email(String address) {
        return new Sensitive(Kind.EMAIL, address);
    }

    String masked() {
        return switch (kind) {
            case AADHAAR -> "XXXX XXXX " + last4();
            case CARD -> "XXXX XXXX XXXX " + last4();
            case ACCOUNT, MOBILE -> "X".repeat(Math.max(0, raw.length() - 4)) + last4();
            case EMAIL -> {
                int at = raw.indexOf('@');
                yield at < 1 ? "***" : raw.charAt(0) + "***" + raw.substring(at);
            }
        };
    }

    /** Fewer than 8 characters is too short to show any of it safely. */
    private String last4() {
        return raw.length() < 8 ? "XXXX" : raw.substring(raw.length() - 4);
    }

    /** Logs, exception messages and debuggers print this: masked too. */
    @Override
    public String toString() {
        return masked();
    }

    static final class MaskingSerializer extends ValueSerializer<Sensitive> {
        @Override
        public void serialize(Sensitive value, JsonGenerator gen, SerializationContext ctxt) {
            gen.writeString(value.masked());
        }
    }
}
