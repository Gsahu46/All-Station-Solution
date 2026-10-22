package com.kartwala.orders;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

import java.time.Instant;
import java.util.List;
import java.util.Locale;

/**
 * Two versions of one resource, side by side. v1 is frozen: its field names, types and values are what old app
 * versions parse, so it only ever gains fields. v2 is where the new shape lives. Both read the same Order.
 */
@RestController
class OrderController {

    /** The shape apps up to 5.x parse. Do not rename, retype or remove anything here. */
    record OrderV1(long id, String customerName, long total, String status, List<ItemV1> items, String trackingUrl) {
    }

    record ItemV1(String sku, int qty, long price) {
    }

    /** The new shape: money in paise, the customer as an object, lower-case states. */
    record OrderV2(long id, CustomerV2 customer, List<ItemV2> items, long totalPaise, String currency, String status, Instant placedAt, String trackingUrl) {
    }

    record CustomerV2(String name, String phone) {
    }

    record ItemV2(String sku, int quantity, long unitPricePaise) {
    }

    private final Orders orders;

    OrderController(Orders orders) {
        this.orders = orders;
    }

    @GetMapping(path = "/{version}/orders/{id}", version = "1")
    OrderV1 v1(@PathVariable long id) {
        Orders.Order o = orders.get(id);
        // Money is integer paise everywhere now, and states are written one way in every version: no more decimals.
        return new OrderV1(o.id(), o.customerName(), o.totalPaise(), status(o),
                o.lines().stream().map(l -> new ItemV1(l.sku(), l.quantity(), l.unitPricePaise())).toList(),
                o.trackingUrl());
    }

    @GetMapping(path = "/{version}/orders/{id}", version = "2")
    OrderV2 v2(@PathVariable long id) {
        Orders.Order o = orders.get(id);
        return new OrderV2(o.id(), new CustomerV2(o.customerName(), o.customerPhone()),
                o.lines().stream().map(l -> new ItemV2(l.sku(), l.quantity(), l.unitPricePaise())).toList(),
                o.totalPaise(), "INR", status(o), o.placedAt(), o.trackingUrl());
    }

    private static String status(Orders.Order o) {
        return o.status().name().toLowerCase(Locale.ROOT);
    }
}
