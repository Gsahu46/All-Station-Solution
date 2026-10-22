package com.kartwala.orders;

import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.stereotype.Component;
import org.springframework.web.ErrorResponseException;

import java.time.Instant;
import java.util.List;
import java.util.Map;

/** The orders themselves, one model for every API version. Demo data in memory: this station is about the API. */
@Component
class Orders {

    enum Status { PLACED, SHIPPED, DELIVERED }

    record Line(String sku, int quantity, long unitPricePaise) {
    }

    record Order(long id, String customerName, String customerPhone, List<Line> lines, Status status, Instant placedAt, String trackingUrl) {
        long totalPaise() {
            return lines.stream().mapToLong(l -> l.quantity() * l.unitPricePaise()).sum();
        }
    }

    private final Map<Long, Order> orders = Map.of(
            1001L, new Order(1001, "Meera Iyer", "+919800000001",
                    List.of(new Line("KW-TEE-01", 2, 49975), new Line("KW-CAP-07", 1, 30000)),
                    Status.SHIPPED, Instant.parse("2026-10-20T09:15:00Z"), "https://track.example/KW1001"),
            1002L, new Order(1002, "Arjun Rao", "+919800000002",
                    List.of(new Line("KW-MUG-03", 4, 24900)), Status.PLACED, Instant.parse("2026-10-21T14:40:00Z"), null));

    Order get(long id) {
        Order o = orders.get(id);
        if (o == null) {
            throw new ErrorResponseException(HttpStatus.NOT_FOUND, ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, "No such order"), null);
        }
        return o;
    }
}
