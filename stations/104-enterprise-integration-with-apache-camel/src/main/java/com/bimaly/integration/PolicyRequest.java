package com.bimaly.integration;

import java.time.LocalDate;

/** One valid line of a bank's file, as the policy-issuance team receives it. */
record PolicyRequest(String bank, String reference, String customerName, LocalDate dateOfBirth, String productCode,
                     long sumInsuredPaise) {

    /** The same line always gets the same id, so the reader can drop a copy it already has. */
    String messageId() {
        return bank + ":" + reference;
    }
}
