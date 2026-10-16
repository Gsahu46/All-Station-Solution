package com.dakroute.shipments;

import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

/** An Indian mobile number as support types it, reduced to the 10 digits the table stores. */
final class PhoneNumber {

    private PhoneNumber() {
    }

    static String normalise(String typed) {
        String digits = typed.replaceAll("[\\s()-]", "");
        if (digits.startsWith("+91") && digits.length() == 13) {
            digits = digits.substring(3);
        } else if (digits.startsWith("0") && digits.length() == 11) {
            digits = digits.substring(1);
        }
        if (!digits.matches("[6-9][0-9]{9}")) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Not an Indian mobile number: " + typed);
        }
        return digits;
    }
}
