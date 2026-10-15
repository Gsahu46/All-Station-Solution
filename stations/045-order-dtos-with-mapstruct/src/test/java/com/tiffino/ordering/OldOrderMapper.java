package com.tiffino.ordering;

import java.util.ArrayList;
import java.util.List;

/**
 * The hand-written mapping before the fix, kept only in tests (600 lines in the real app; the order part is enough).
 * Written before delivery instructions existed. The field was added to the entity, the request and the response in
 * March, and nobody came back here. It compiles, it runs, and the instructions are dropped both ways.
 */
final class OldOrderMapper {

    /** The response class as it was then: it has the field, but the mapper below never fills it. */
    record OldResponse(long id, String customerName, String phone, OrderDtos.AddressDto address, String deliveryInstructions,
                       List<OrderDtos.LineResponse> lines, long totalPaise, String status) {
    }

    private OldOrderMapper() {
    }

    static Order toEntity(OrderDtos.CreateOrderRequest r) {
        Order order = new Order();
        order.setCustomerName(r.customerName());
        order.setPhone(r.phone());
        Address address = new Address();
        address.setLine(r.address().line());
        address.setCity(r.address().city());
        address.setPincode(r.address().pincode());
        order.setAddress(address);
        List<OrderLine> lines = new ArrayList<>();
        for (OrderDtos.LineRequest l : r.lines()) {
            OrderLine line = new OrderLine();
            line.setItem(l.item());
            line.setQuantity(l.quantity());
            line.setUnitPricePaise(l.unitPricePaise());
            line.setOrder(order);
            lines.add(line);
        }
        order.setLines(lines);
        return order;
    }

    static OldResponse toResponse(Order o) {
        List<OrderDtos.LineResponse> lines = o.getLines().stream()
                .map(l -> new OrderDtos.LineResponse(l.getItem(), l.getQuantity(), l.getUnitPricePaise(), l.getQuantity() * l.getUnitPricePaise()))
                .toList();
        OrderDtos.AddressDto address = new OrderDtos.AddressDto(o.getAddress().getLine(), o.getAddress().getCity(), o.getAddress().getPincode());
        return new OldResponse(o.getId() == null ? 0 : o.getId(), o.getCustomerName(), "******" + o.getPhone().substring(6),
                address, null, lines, o.getTotalPaise(), o.getStatus());   // the constructor took null for the new argument
    }
}
