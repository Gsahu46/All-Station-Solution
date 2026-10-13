package com.basketo.stores;

import org.springframework.stereotype.Component;

import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Optional;

@Component
class StoreDirectory {

    private final Map<String, StoreStatus> stores = Map.of(
            "BLR-KOR-01", StoreStatus.open("BLR-KOR-01", "Koramangala", 10),
            "BLR-IND-01", StoreStatus.closed("BLR-IND-01", "Indiranagar", "Closed for stock-taking"),
            "BLR-HSR-02", StoreStatus.open("BLR-HSR-02", "HSR Layout", 15),
            "DEL-SAK-01", StoreStatus.open("DEL-SAK-01", "Saket", 12));

    Optional<StoreStatus> find(String storeId) {
        return Optional.ofNullable(stores.get(storeId));
    }

    /** Challenge 2. Map.of has no order, so sort explicitly: the same request must give the same list. */
    List<StoreStatus> inCity(String city) {
        return stores.values().stream()
                .filter(s -> s.storeId().startsWith(city + "-"))
                .sorted(Comparator.comparing(StoreStatus::storeId))
                .toList();
    }
}
