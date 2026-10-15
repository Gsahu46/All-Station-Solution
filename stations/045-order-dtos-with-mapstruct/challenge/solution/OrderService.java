package com.tiffino.ordering;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.Optional;

@Service
class OrderService {

    private final OrderRepository orders;
    private final OrderMapper mapper;

    OrderService(OrderRepository orders, OrderMapper mapper) {
        this.orders = orders;
        this.mapper = mapper;
    }

    /** Records an order (a demo record; no kitchen, no payment). The total is computed here, from the lines. */
    @Transactional
    OrderDtos.OrderResponse place(OrderDtos.CreateOrderRequest request) {
        Order order = mapper.toEntity(request);
        order.setStatus("PLACED");
        order.setTotalPaise(order.getLines().stream().mapToLong(l -> Math.multiplyExact((long) l.getQuantity(), l.getUnitPricePaise())).sum()
                + order.getTipPaise());
        return mapper.toResponse(orders.save(order));
    }

    @Transactional(readOnly = true)
    Optional<OrderDtos.KitchenTicket> ticket(long id) {
        return orders.findById(id).map(mapper::toTicket);
    }

    /** Mapped inside the transaction: the lines are loaded while the session is open. */
    @Transactional(readOnly = true)
    Optional<OrderDtos.OrderResponse> find(long id) {
        return orders.findById(id).map(mapper::toResponse);
    }
}
