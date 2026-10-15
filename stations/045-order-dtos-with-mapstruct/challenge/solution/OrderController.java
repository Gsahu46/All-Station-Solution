package com.tiffino.ordering;

import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.net.URI;

@RestController
class OrderController {

    private final OrderService service;

    OrderController(OrderService service) {
        this.service = service;
    }

    @PostMapping("/orders")
    ResponseEntity<OrderDtos.OrderResponse> place(@Valid @RequestBody OrderDtos.CreateOrderRequest request) {
        OrderDtos.OrderResponse placed = service.place(request);
        return ResponseEntity.created(URI.create("/orders/" + placed.id())).body(placed);
    }

    @GetMapping("/orders/{id}/kitchen-ticket")
    OrderDtos.KitchenTicket ticket(@PathVariable long id) {
        return service.ticket(id).orElseThrow(() -> {
            ProblemDetail p = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, "No order " + id + ".");
            p.setTitle("Order not found");
            return new ErrorResponseException(HttpStatus.NOT_FOUND, p, null);
        });
    }

    @GetMapping("/orders/{id}")
    OrderDtos.OrderResponse one(@PathVariable long id) {
        return service.find(id).orElseThrow(() -> {
            ProblemDetail p = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, "No order " + id + ".");
            p.setTitle("Order not found");
            return new ErrorResponseException(HttpStatus.NOT_FOUND, p, null);
        });
    }
}
