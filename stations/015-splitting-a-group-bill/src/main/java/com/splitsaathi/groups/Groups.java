package com.splitsaathi.groups;

import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

/** Groups and their expenses, in memory. Each expense stores who owes what, already split, so balances never re-divide. */
@Component
class Groups {

    record Expense(UUID id, String description, String paidBy, long amountPaise, Map<String, Long> owedPaise) {
    }

    record Group(long id, String name, List<String> members, List<Expense> expenses) {
    }

    private final Map<Long, Group> groups = Map.of(
            1L, new Group(1, "Goa trip", List.of("asha", "kabir", "meera", "ravi"), new ArrayList<>()),
            2L, new Group(2, "Flat 302", List.of("neha", "omar"), new ArrayList<>()));

    Optional<Group> find(long id) {
        return Optional.ofNullable(groups.get(id));
    }

    synchronized Expense add(Group g, String description, String paidBy, long amountPaise, Map<String, Long> owed) {
        Expense e = new Expense(UUID.randomUUID(), description, paidBy, amountPaise, owed);
        g.expenses().add(e);
        return e;
    }

    /** Net balance per member: what they paid minus what they owe. Positive: others owe them. Always sums to zero. */
    synchronized Map<String, Long> balances(Group g) {
        Map<String, Long> net = new LinkedHashMap<>();
        g.members().forEach(m -> net.put(m, 0L));
        for (Expense e : g.expenses()) {
            net.merge(e.paidBy(), e.amountPaise(), Long::sum);
            e.owedPaise().forEach((who, owes) -> net.merge(who, -owes, Long::sum));
        }
        return net;
    }

    /** For tests only. */
    synchronized void clear() {
        groups.values().forEach(g -> g.expenses().clear());
    }
}
