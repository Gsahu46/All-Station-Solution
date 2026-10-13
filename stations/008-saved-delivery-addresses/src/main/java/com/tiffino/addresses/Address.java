package com.tiffino.addresses;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

/**
 * A saved address: both the PUT body and the stored value. The label is not in the body: it is the last part
 * of the URL, which names the address. No "updatedAt" or version on purpose: sending the same PUT twice must
 * leave exactly the same state, and a timestamp would differ.
 */
public record Address(
        @NotBlank @Size(max = 100) String line1,
        @Size(max = 100) String line2,
        @Size(max = 60) String landmark,
        @NotBlank @Size(max = 50) String city,
        @NotBlank @Pattern(regexp = "[1-9]\\d{5}", message = "must be a 6-digit PIN code") String pincode) {

    public Address {
        line1 = strip(line1);
        city = strip(city);
        pincode = strip(pincode);
        line2 = optional(line2);
        landmark = optional(landmark);
    }

    private static String strip(String s) {
        return s == null ? null : s.strip();
    }

    /** A blank optional field means "none", stored as null, so "" and a missing field are the same address. */
    private static String optional(String s) {
        return s == null || s.isBlank() ? null : s.strip();
    }
}
