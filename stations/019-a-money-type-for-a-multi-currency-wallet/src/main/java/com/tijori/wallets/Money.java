package com.tijori.wallets;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonPropertyOrder;

import java.math.BigDecimal;
import java.util.Currency;
import java.util.Objects;

/**
 * An amount in one currency, as a value object: immutable, compared by value. Stored as whole minor units
 * (paise, cents; yen have none), so 10.5 and 10.50 rupees are the same 1,050 paise and the same Money.
 */
@JsonPropertyOrder({"amount", "currency", "minorUnits"})
record Money(long minorUnits, Currency currency) {

    Money {
        Objects.requireNonNull(currency, "currency");
    }

    /**
     * "10.5" INR becomes 1,050 paise. setScale without a rounding mode refuses to drop digits, so "10.505" INR
     * or "100.5" JPY throws instead of silently becoming something else.
     */
    static Money parse(String amount, Currency currency) {
        BigDecimal exact = new BigDecimal(amount).setScale(currency.getDefaultFractionDigits());
        return new Money(exact.unscaledValue().longValueExact(), currency);
    }

    /** Adding is only defined within one currency. Rupees plus dollars is a bug, not a number. */
    Money plus(Money other) {
        if (!currency.equals(other.currency)) {
            throw new CurrencyMismatchException(this, other);
        }
        return new Money(Math.addExact(minorUnits, other.minorUnits), currency);
    }

    /** "10.50" for INR, "100" for JPY: always the currency's own number of decimals. */
    @JsonProperty("amount")
    String amount() {
        return BigDecimal.valueOf(minorUnits, currency.getDefaultFractionDigits()).toPlainString();
    }

    @Override
    public String toString() {
        return amount() + " " + currency.getCurrencyCode();
    }

    static final class CurrencyMismatchException extends IllegalArgumentException {
        CurrencyMismatchException(Money a, Money b) {
            super("Cannot combine " + a + " with " + b + ": different currencies.");
        }
    }
}
