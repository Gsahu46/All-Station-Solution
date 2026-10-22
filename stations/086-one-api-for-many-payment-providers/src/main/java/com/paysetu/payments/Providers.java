package com.paysetu.payments;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;

/** Picks adapters by name from configuration. Switching provider is a config change; a wrong name stops the app at start. */
@Component
class Providers {

    private final Map<String, PaymentProvider> byName;
    private final List<PaymentProvider> inOrder;

    Providers(List<PaymentProvider> all, @Value("${paysetu.primary}") String primary, @Value("${paysetu.fallback:}") String fallback) {
        this.byName = all.stream().collect(Collectors.toMap(PaymentProvider::name, Function.identity()));
        this.inOrder = fallback.isBlank() ? List.of(named(primary)) : List.of(named(primary), named(fallback));
    }

    /** The primary, then the fallback if there is one. */
    List<PaymentProvider> inOrder() {
        return inOrder;
    }

    /** The adapter for a stored payment: refunds and status checks go to the provider that took it, whatever is primary now. */
    PaymentProvider named(String name) {
        PaymentProvider p = byName.get(name);
        if (p == null) {
            throw new IllegalStateException("No payment provider named " + name + "; known: " + byName.keySet().stream().sorted().toList());
        }
        return p;
    }
}
