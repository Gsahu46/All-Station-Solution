package com.tiffino.ordering;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import java.util.List;

/** The API's shapes: what a client sends, and what it gets back. Separate from the entities on purpose. */
final class OrderDtos {

    private OrderDtos() {
    }

    record AddressDto(@NotBlank @Size(max = 200) String line,
                      @NotBlank @Size(max = 40) String city,
                      @NotNull @Pattern(regexp = "[1-9]\\d{5}", message = "must be a 6-digit PIN code") String pincode) {
    }

    record LineRequest(@NotBlank @Size(max = 80) String item,
                       @NotNull @Min(1) @Max(20) Integer quantity,
                       @NotNull @Min(1) Long unitPricePaise) {
    }

    record CreateOrderRequest(@NotBlank @Size(max = 80) String customerName,
                              @NotNull @Pattern(regexp = "[6-9]\\d{9}", message = "must be a 10-digit mobile number") String phone,
                              @NotNull @Valid AddressDto address,
                              @Size(max = 200) String deliveryInstructions,
                              @NotEmpty @Size(max = 20) List<@NotNull @Valid LineRequest> lines) {
    }

    record LineResponse(String item, int quantity, long unitPricePaise, long linePaise) {
    }

    record OrderResponse(long id, String customerName, String phone, AddressDto address, String deliveryInstructions,
                         List<LineResponse> lines, long totalPaise, String status) {
    }
}
