package com.basketo.stores;

/**
 * What the app needs to decide whether to promise a delivery. A record becomes JSON as-is:
 * {"storeId":"BLR-KOR-01","name":"Koramangala","open":true,"reason":null,"deliveryPromiseMinutes":10}
 */
public record StoreStatus(String storeId, String name, boolean open, String reason, Integer deliveryPromiseMinutes) {

    static StoreStatus open(String storeId, String name, int deliveryPromiseMinutes) {
        return new StoreStatus(storeId, name, true, null, deliveryPromiseMinutes);
    }

    /** A closed store makes no delivery promise: the app must not show "10 minutes". */
    static StoreStatus closed(String storeId, String name, String reason) {
        return new StoreStatus(storeId, name, false, reason, null);
    }
}
