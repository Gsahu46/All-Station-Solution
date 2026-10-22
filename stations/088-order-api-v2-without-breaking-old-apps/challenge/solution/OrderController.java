package com.kartwala.orders;

import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RestController;

import java.math.BigDecimal;
import java.time.Clock;
import java.time.Instant;
import java.time.LocalDate;
import java.time.format.DateTimeParseException;
import java.util.List;
import java.util.Locale;

/**
 * Two versions of one resource, side by side. v1 is frozen: its field names, types and values are what old app
 * versions parse, so it only ever gains fields. v2 is where the new shape lives. Both read the same Order.
 */
@RestController
class OrderController {

    /** The shape apps up to 5.x parse. Do not rename, retype or remove anything here. */
    record OrderV1(long id, String customerName, BigDecimal total, String status, List<ItemV1> items, String trackingUrl) {
    }

    record ItemV1(String sku, int qty, BigDecimal price) {
    }

    /** The new shape: money in paise, the customer as an object, lower-case states. */
    record OrderV2(long id, CustomerV2 customer, List<ItemV2> items, long totalPaise, String currency, String status, Instant placedAt, String trackingUrl) {
    }

    record CustomerV2(String name, String phone) {
    }

    record ItemV2(String sku, int quantity, long unitPricePaise) {
    }

    /** The day the v2 shape was released: dated versions before it get the v1 shape. */
    static final LocalDate V2_RELEASED = LocalDate.of(2026, 10, 1);

    private final Orders orders;
    private final Clock clock;

    OrderController(Orders orders, Clock clock) {
        this.orders = orders;
        this.clock = clock;
    }

    @GetMapping(path = "/{version}/orders/{id}", version = "1")
    OrderV1 v1(@PathVariable long id) {
        if (!clock.instant().isBefore(ApiVersions.V1_SUNSET.toInstant())) {
            ProblemDetail gone = ProblemDetail.forStatusAndDetail(HttpStatus.GONE, "Orders API v1 ended on 1 Apr 2027. Use v2: " + ApiVersions.MIGRATION_GUIDE);
            throw new ErrorResponseException(HttpStatus.GONE, gone, null);
        }
        return v1Shape(id);
    }

    /** Stripe-style dated versions: the shape that was current on the date in the header. */
    @GetMapping("/orders/{id}")
    Object dated(@PathVariable long id, @RequestHeader("Kartwala-Version") String version) {
        LocalDate date;
        try {
            date = LocalDate.parse(version);
        } catch (DateTimeParseException e) {
            throw new ErrorResponseException(HttpStatus.BAD_REQUEST, ProblemDetail.forStatusAndDetail(HttpStatus.BAD_REQUEST, "Kartwala-Version must be a date like 2026-10-01"), e);
        }
        return date.isBefore(V2_RELEASED) ? v1Shape(id) : v2(id);
    }

    private OrderV1 v1Shape(long id) {
        Orders.Order o = orders.get(id);
        // v1 sent rupees as a decimal number; kept exactly (BigDecimal from paise), never through a double.
        return new OrderV1(o.id(), o.customerName(), BigDecimal.valueOf(o.totalPaise(), 2), o.status().name(),
                o.lines().stream().map(l -> new ItemV1(l.sku(), l.quantity(), BigDecimal.valueOf(l.unitPricePaise(), 2))).toList(),
                o.trackingUrl());
    }

    @GetMapping(path = "/{version}/orders/{id}", version = "2")
    OrderV2 v2(@PathVariable long id) {
        Orders.Order o = orders.get(id);
        return new OrderV2(o.id(), new CustomerV2(o.customerName(), o.customerPhone()),
                o.lines().stream().map(l -> new ItemV2(l.sku(), l.quantity(), l.unitPricePaise())).toList(),
                o.totalPaise(), "INR", o.status().name().toLowerCase(Locale.ROOT), o.placedAt(), o.trackingUrl());
    }
}
