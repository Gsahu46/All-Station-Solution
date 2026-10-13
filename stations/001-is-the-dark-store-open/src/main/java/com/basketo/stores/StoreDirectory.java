package com.basketo.stores;

import org.springframework.stereotype.Component;

import java.util.Map;
import java.util.Optional;

/**
 * Every dark store and its current status. In-memory for this station: a real system reads this from the
 * store-operations database, which later stations add. Optional makes "no such store" impossible to ignore.
 */
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
}
