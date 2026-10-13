package com.splitsaathi.groups;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/**
 * Turns net balances into payments. Greedy: the person who owes the most pays the person owed the most, as much as
 * one of them needs; repeat. Each payment settles at least one person, so n people need at most n - 1 payments.
 * (The true minimum is a much harder problem in general; this bound is what apps like this use in practice.)
 */
final class SettleUp {

    record Payment(String from, String to, long amountPaise) {
    }

    private SettleUp() {
    }

    /** balances: positive = is owed money, negative = owes money. They must add up to zero. */
    static List<Payment> payments(Map<String, Long> balances) {
        if (balances.values().stream().mapToLong(Long::longValue).sum() != 0) {
            throw new IllegalStateException("balances do not add up to zero");
        }
        Map<String, Long> left = new TreeMap<>(balances); // sorted by name, so ties always resolve the same way
        List<Payment> payments = new ArrayList<>();
        while (true) {
            var debtor = left.entrySet().stream().min(Comparator.comparingLong(Map.Entry::getValue)).orElseThrow();
            var creditor = left.entrySet().stream().max(Comparator.comparingLong(Map.Entry::getValue)).orElseThrow();
            if (creditor.getValue() == 0) {
                return payments;
            }
            long amount = Math.min(-debtor.getValue(), creditor.getValue());
            payments.add(new Payment(debtor.getKey(), creditor.getKey(), amount));
            left.put(debtor.getKey(), debtor.getValue() + amount);
            left.put(creditor.getKey(), creditor.getValue() - amount);
        }
    }
}
