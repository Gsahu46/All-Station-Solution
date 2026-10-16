package com.tijori.notifications;

import org.springframework.stereotype.Component;

import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

/** Demo customers (invented) and their preferences. shortcut: in memory; a real bank reads its customer system. */
@Component
class Customers {

    private final Map<Long, Model.Customer> customers = Map.of(
            1L, new Model.Customer(1, "Asha Verma", "4821", "9876543210", "Asha.Verma@example.in", "device-token-asha"),
            2L, new Model.Customer(2, "Rohan Iyer", "7730", "9123456780", null, null));   // no email, no app
    private final Map<Long, Model.Preferences> preferences = new ConcurrentHashMap<>();

    Customers() {
        reset();
    }

    final void reset() {
        preferences.put(1L, new Model.Preferences(true, true, true));
        preferences.put(2L, new Model.Preferences(true, true, false));
    }

    Optional<Model.Customer> find(long id) {
        return Optional.ofNullable(customers.get(id));
    }

    Model.Preferences preferencesOf(long id) {
        return preferences.get(id);
    }

    void setPreferences(long id, Model.Preferences p) {
        preferences.put(id, p);
    }
}
