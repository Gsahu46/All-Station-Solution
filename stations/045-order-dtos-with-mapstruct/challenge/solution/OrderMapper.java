package com.tiffino.ordering;

import org.mapstruct.AfterMapping;
import org.mapstruct.Mapper;
import org.mapstruct.Mapping;
import org.mapstruct.MappingConstants;
import org.mapstruct.MappingTarget;
import org.mapstruct.Named;
import org.mapstruct.ReportingPolicy;

/**
 * MapStruct writes the implementation at compile time. unmappedTargetPolicy = ERROR is the point of this station: if
 * a field is added to an entity or a response and nobody says where it comes from (or that it is ignored on
 * purpose), the build fails, naming the field. A hand-written mapper just leaves it null.
 */
@Mapper(componentModel = MappingConstants.ComponentModel.SPRING, unmappedTargetPolicy = ReportingPolicy.ERROR)
interface OrderMapper {

    @Mapping(target = "id", ignore = true)            // the database assigns it
    @Mapping(target = "status", ignore = true)        // set by the service
    @Mapping(target = "totalPaise", ignore = true)    // computed by the service, never taken from the client
    @Mapping(target = "tipPaise", source = "tipPaise", defaultValue = "0L")   // MapStruct insists on the L for a long
    Order toEntity(OrderDtos.CreateOrderRequest request);

    @Mapping(target = "id", ignore = true)
    @Mapping(target = "order", ignore = true)         // linked back in linkLines
    OrderLine toEntity(OrderDtos.LineRequest line);

    Address toEntity(OrderDtos.AddressDto address);

    /** Each line must point at its order, or Hibernate cannot fill order_id. */
    @AfterMapping
    default void linkLines(@MappingTarget Order order) {
        order.getLines().forEach(line -> line.setOrder(order));
    }

    @Mapping(target = "phone", source = "phone", qualifiedByName = "maskPhone")
    OrderDtos.OrderResponse toResponse(Order order);

    @Mapping(target = "linePaise", expression = "java(line.getQuantity() * line.getUnitPricePaise())")
    OrderDtos.LineResponse toResponse(OrderLine line);

    OrderDtos.AddressDto toDto(Address address);

    @Mapping(target = "orderId", source = "id")
    @Mapping(target = "items", source = "lines")
    @Mapping(target = "instructions", source = "deliveryInstructions")
    OrderDtos.KitchenTicket toTicket(Order order);

    /** Used by toTicket for each line: "2 x Paneer thali". */
    default String ticketLine(OrderLine line) {
        return line.getQuantity() + " x " + line.getItem();
    }

    /** Only the last four digits leave the server. */
    @Named("maskPhone")
    static String maskPhone(String phone) {
        return "******" + phone.substring(phone.length() - 4);
    }
}
