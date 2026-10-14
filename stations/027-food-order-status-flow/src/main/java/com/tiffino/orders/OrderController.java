package com.tiffino.orders;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.util.Comparator;

@RestController
class OrderController {

    record StatusChange(@NotNull OrderStatus to) {
    }

    private final Orders orders;

    OrderController(Orders orders) {
        this.orders = orders;
    }

    @GetMapping("/orders/{id}")
    Orders.Order order(@PathVariable long id) {
        return orders.find(id).orElseThrow(() -> notFound(id));
    }

    /** 200 with the order after the move; 409 when the table does not allow it, naming what is allowed. */
    @PostMapping("/orders/{id}/status-changes")
    Orders.Order change(@PathVariable long id, @Valid @RequestBody StatusChange change) {
        try {
            return orders.move(id, change.to()).orElseThrow(() -> notFound(id));
        } catch (Orders.IllegalMove e) {
            String allowed = e.from.next().stream().sorted(Comparator.naturalOrder()).map(Enum::name).toList().toString();
            ProblemDetail p = ProblemDetail.forStatusAndDetail(HttpStatus.CONFLICT,
                    e.getMessage() + (e.from.isTerminal() ? " It is " + e.from + ": nothing can change now." : " Allowed next: " + allowed + "."));
            p.setTitle("Status change not allowed");
            p.setProperty("currentStatus", e.from);
            p.setProperty("allowedNext", e.from.next());
            throw new ErrorResponseException(HttpStatus.CONFLICT, p, e);
        }
    }

    private static ErrorResponseException notFound(long id) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, "No order " + id + ".");
        p.setTitle("Order not found");
        return new ErrorResponseException(HttpStatus.NOT_FOUND, p, null);
    }
}
