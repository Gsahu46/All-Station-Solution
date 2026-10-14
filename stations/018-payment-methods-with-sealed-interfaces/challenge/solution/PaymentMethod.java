package com.paysetu.payments;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonSubTypes;
import com.fasterxml.jackson.annotation.JsonTypeInfo;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;

import java.util.Locale;

/**
 * Exactly one of four ways to pay. "sealed ... permits" closes the list: a switch over PaymentMethod with no default
 * must handle every record, and adding a fifth method is a compile error everywhere one is forgotten.
 * JSON carries a "type" field that picks the record; each record has only the fields its method needs.
 */
@JsonTypeInfo(use = JsonTypeInfo.Id.NAME, property = "type")
@JsonSubTypes({
        @JsonSubTypes.Type(value = PaymentMethod.Upi.class, name = "UPI"),
        @JsonSubTypes.Type(value = PaymentMethod.Card.class, name = "CARD"),
        @JsonSubTypes.Type(value = PaymentMethod.NetBanking.class, name = "NET_BANKING"),
        @JsonSubTypes.Type(value = PaymentMethod.Wallet.class, name = "WALLET"),
        @JsonSubTypes.Type(value = PaymentMethod.PayLater.class, name = "PAY_LATER")})
sealed interface PaymentMethod
        permits PaymentMethod.Upi, PaymentMethod.Card, PaymentMethod.NetBanking, PaymentMethod.Wallet, PaymentMethod.PayLater {

    /** A UPI ID such as asha@okaxis, stored lower-case. */
    record Upi(@NotNull @Pattern(regexp = "[A-Za-z0-9._-]{2,64}@[A-Za-z][A-Za-z0-9]{1,63}", message = "must be a UPI ID like name@bank") String vpa)
            implements PaymentMethod {
        public Upi {
            vpa = vpa == null ? null : vpa.toLowerCase(Locale.ROOT);
        }
    }

    /**
     * A saved card, as a token from the (simulated) card network plus what may be shown: network and last 4 digits.
     * The full card number never reaches this API, and the token is accepted but never written back out.
     */
    record Card(@NotNull Network network,
                @NotNull @Pattern(regexp = "\\d{4}", message = "must be the last 4 digits") String last4,
                @NotNull @Pattern(regexp = "tok_[A-Za-z0-9]{8,64}", message = "must be a card token") @JsonProperty(access = JsonProperty.Access.WRITE_ONLY) String token)
            implements PaymentMethod {
        enum Network { VISA, MASTERCARD, RUPAY }
    }

    /** Net banking at a bank, by the 4-letter bank code that starts its IFSC codes (HDFC, SBIN...), stored upper-case. */
    record NetBanking(@NotNull @Pattern(regexp = "[A-Za-z]{4}", message = "must be a 4-letter bank code") String bankCode)
            implements PaymentMethod {
        public NetBanking {
            bankCode = bankCode == null ? null : bankCode.toUpperCase(Locale.ROOT);
        }
    }

    /** The Paysetu wallet of a mobile number. Responses show the number masked. */
    record Wallet(@NotNull @Pattern(regexp = "[6-9]\\d{9}", message = "must be a 10-digit Indian mobile number")
                  @JsonProperty(access = JsonProperty.Access.WRITE_ONLY) String mobile)
            implements PaymentMethod {
        @JsonProperty("maskedMobile")
        String maskedMobile() {
            return mobile.substring(0, 2) + "******" + mobile.substring(8);
        }
    }

    /** Challenge 2: Paysetu Pay Later (fictional), by mobile number, shown masked. */
    record PayLater(@NotNull @Pattern(regexp = "[6-9]\\d{9}", message = "must be a 10-digit Indian mobile number")
                    @JsonProperty(access = JsonProperty.Access.WRITE_ONLY) String mobile)
            implements PaymentMethod {
        @JsonProperty("maskedMobile")
        String maskedMobile() {
            return mobile.substring(0, 2) + "******" + mobile.substring(8);
        }
    }
}
