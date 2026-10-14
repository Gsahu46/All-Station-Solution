package com.tijori.wallets;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.util.Comparator;
import java.util.Currency;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

@RestController
class WalletController {

    /** Currencies this demo wallet holds. JPY is here to show a currency with no minor unit. */
    static final Set<String> SUPPORTED = Set.of("INR", "USD", "AED", "JPY");

    /** The amount is a string: a JSON number can pass through a double in some clients and arrive as 10.499999. */
    record CreditRequest(@NotNull @Pattern(regexp = "\\d{1,6}(\\.\\d{1,4})?", message = "must be a decimal string like \"10.50\", at most 999999 (a demo rule)") String amount,
                         @NotNull @Pattern(regexp = "[A-Za-z]{3}", message = "must be a 3-letter ISO 4217 code") String currency,
                         @NotNull @Size(min = 1, max = 40) String reference) {
    }

    record Credited(String walletId, String reference, Money credited, Money balance) {
    }

    record Balances(String walletId, List<Money> balances) {
    }

    /** Two demo wallets, each a balance per currency. Gone when the app stops. */
    private final Map<String, Map<Currency, Money>> wallets = Map.of(
            "w-asha", new ConcurrentHashMap<>(), "w-ravi", new ConcurrentHashMap<>());

    @PostMapping("/wallets/{id}/credits")
    @ResponseStatus(HttpStatus.CREATED)
    Credited credit(@PathVariable String id, @Valid @RequestBody CreditRequest r) {
        String walletId = id.toLowerCase(Locale.ROOT);
        Map<Currency, Money> wallet = wallet(walletId);
        String code = r.currency().toUpperCase(Locale.ROOT);
        if (!SUPPORTED.contains(code)) {
            throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "Currency not supported",
                    "This wallet holds " + String.join(", ", SUPPORTED.stream().sorted().toList()) + ", not " + code + ".");
        }
        Currency currency = Currency.getInstance(code);
        Money credit;
        try {
            credit = Money.parse(r.amount(), currency);
        } catch (ArithmeticException tooPrecise) {
            throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "Too many decimal places",
                    code + " amounts have " + currency.getDefaultFractionDigits() + " decimal places; " + r.amount() + " has more.");
        }
        if (credit.minorUnits() == 0) {
            throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "Nothing to credit", "The amount must be more than zero.");
        }
        Money balance = wallet.merge(currency, credit, Money::plus);   // atomic per currency in a ConcurrentHashMap
        return new Credited(walletId, r.reference(), credit, balance);
    }

    /** One balance per currency, never added together: there is no exchange rate in this station. */
    @GetMapping("/wallets/{id}/balance")
    Balances balance(@PathVariable String id) {
        String walletId = id.toLowerCase(Locale.ROOT);
        return new Balances(walletId, wallet(walletId).values().stream()
                .sorted(Comparator.comparing(m -> m.currency().getCurrencyCode())).toList());
    }

    private Map<Currency, Money> wallet(String id) {
        Map<Currency, Money> wallet = wallets.get(id);
        if (wallet == null) {
            throw problem(HttpStatus.NOT_FOUND, "Wallet not found", "No wallet has the id " + id + ".");
        }
        return wallet;
    }

    /** Empties every wallet. Used by the tests, so each starts from zero. */
    void clear() {
        wallets.values().forEach(Map::clear);
    }

    private static ErrorResponseException problem(HttpStatus status, String title, String detail) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(status, detail);
        p.setTitle(title);
        return new ErrorResponseException(status, p, null);
    }
}
