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
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import com.fasterxml.jackson.annotation.JsonInclude;

import java.math.BigDecimal;
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

    record Debited(String walletId, String reference, Money debited, Money balance) {
    }

    @JsonInclude(JsonInclude.Include.NON_NULL)
    record Balances(String walletId, List<Money> balances, Money indicativeTotal) {
    }

    /** Challenge 2: demo rates in rupees, not market rates. */
    static final Map<String, BigDecimal> DEMO_RATES_IN_INR = Map.of(
            "INR", BigDecimal.ONE, "USD", new BigDecimal("88.00"), "AED", new BigDecimal("24.00"), "JPY", new BigDecimal("0.60"));

    /** Two demo wallets, each a balance per currency. Gone when the app stops. */
    private final Map<String, Map<Currency, Money>> wallets = Map.of(
            "w-asha", new ConcurrentHashMap<>(), "w-ravi", new ConcurrentHashMap<>());

    @PostMapping("/wallets/{id}/credits")
    @ResponseStatus(HttpStatus.CREATED)
    Credited credit(@PathVariable String id, @Valid @RequestBody CreditRequest r) {
        String walletId = id.toLowerCase(Locale.ROOT);
        Map<Currency, Money> wallet = wallet(walletId);
        Money credit = amount(r);
        Money balance = wallet.merge(credit.currency(), credit, Money::plus);   // atomic per currency in a ConcurrentHashMap
        return new Credited(walletId, r.reference(), credit, balance);
    }

    /** Challenge 1: the same body as a credit. compute() is atomic per currency, and throwing inside it changes nothing. */
    @PostMapping("/wallets/{id}/debits")
    @ResponseStatus(HttpStatus.CREATED)
    Debited debit(@PathVariable String id, @Valid @RequestBody CreditRequest r) {
        String walletId = id.toLowerCase(Locale.ROOT);
        Map<Currency, Money> wallet = wallet(walletId);
        Money debit = amount(r);
        Money balance = wallet.compute(debit.currency(), (currency, current) -> {
            if (current == null || current.minorUnits() < debit.minorUnits()) {
                throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "Insufficient balance",
                        "The " + currency.getCurrencyCode() + " balance is " + (current == null ? "zero" : current) + "; cannot take " + debit + ".");
            }
            return current.minus(debit);
        });
        return new Debited(walletId, r.reference(), debit, balance);
    }

    private static Money amount(CreditRequest r) {
        Currency currency = supported(r.currency());
        Money money;
        try {
            money = Money.parse(r.amount(), currency);
        } catch (ArithmeticException tooPrecise) {
            throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "Too many decimal places",
                    currency.getCurrencyCode() + " amounts have " + currency.getDefaultFractionDigits() + " decimal places; " + r.amount() + " has more.");
        }
        if (money.minorUnits() == 0) {
            throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "Amount is zero", "The amount must be more than zero.");
        }
        return money;
    }

    private static Currency supported(String requested) {
        String code = requested.toUpperCase(Locale.ROOT);
        if (!SUPPORTED.contains(code)) {
            throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "Currency not supported",
                    "This wallet holds " + String.join(", ", SUPPORTED.stream().sorted().toList()) + ", not " + code + ".");
        }
        return Currency.getInstance(code);
    }

    /** One balance per currency; with ?in=, also an indicative total converted at demo rates (challenge 2). */
    @GetMapping("/wallets/{id}/balance")
    Balances balance(@PathVariable String id, @RequestParam(required = false) String in) {
        String walletId = id.toLowerCase(Locale.ROOT);
        List<Money> balances = wallet(walletId).values().stream()
                .sorted(Comparator.comparing(m -> m.currency().getCurrencyCode())).toList();
        Money total = null;
        if (in != null) {
            Currency target = supported(in);
            total = balances.stream()
                    .map(m -> m.convertTo(target, DEMO_RATES_IN_INR.get(m.currency().getCurrencyCode()), DEMO_RATES_IN_INR.get(target.getCurrencyCode())))
                    .reduce(new Money(0, target), Money::plus);
        }
        return new Balances(walletId, balances, total);
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
