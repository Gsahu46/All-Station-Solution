package com.tiffino.addresses;

import jakarta.validation.constraints.NotBlank;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

/**
 * Challenge 2: the default address as its own small resource. PUT sets it to a label; sending the same PUT
 * again changes nothing, so a retry is safe. A separate URL keeps "which one is default" out of the address itself.
 */
@RestController
class DefaultAddressController {

    record DefaultAddress(@NotBlank String label) {
    }

    private final AddressBook book;
    private final AddressController addresses;

    DefaultAddressController(AddressBook book, AddressController addresses) {
        this.book = book;
        this.addresses = addresses;
    }

    @PutMapping("/customers/{customerId}/default-address")
    DefaultAddress set(@PathVariable long customerId, @RequestBody DefaultAddress request) {
        addresses.requireCustomer(customerId);
        String label = AddressController.normalise(request.label());
        if (!book.setDefault(customerId, label)) {
            throw AddressController.problem(HttpStatus.CONFLICT, "No such address", "Save an address with this label first.");
        }
        return new DefaultAddress(label);
    }

    @GetMapping("/customers/{customerId}/default-address")
    DefaultAddress get(@PathVariable long customerId) {
        addresses.requireCustomer(customerId);
        return book.defaultLabel(customerId).map(DefaultAddress::new)
                .orElseThrow(() -> AddressController.problem(HttpStatus.NOT_FOUND, "No default address", "No default address is set."));
    }
}
