package com.tijori.beneficiaries;

import java.util.UUID;

/**
 * One exception per thing that can go wrong for a reason the client can act on. They say what happened
 * in business terms; ApiErrors decides the status code and the problem type. None of them carries a stack
 * trace to the client.
 */
final class Exceptions {

    private Exceptions() {
    }

    /** 404. Also thrown for another customer's beneficiary, so the API never confirms it exists. */
    static class BeneficiaryNotFound extends RuntimeException {
        BeneficiaryNotFound(UUID id) {
            super("No beneficiary " + id + " for this customer");
        }
    }

    /** 409. The same account at the same branch is already a beneficiary of this customer. */
    static class DuplicateBeneficiary extends RuntimeException {
        final UUID existingId;

        DuplicateBeneficiary(UUID existingId) {
            super("Already a beneficiary: " + existingId);
            this.existingId = existingId;
        }
    }

    /** 400. Well-formed, but no bank branch has this IFSC. The customer should check the code. */
    static class UnknownIfsc extends RuntimeException {
        UnknownIfsc() {
            super("IFSC not found in the directory");
        }
    }

    /** 503. The IFSC directory could not be asked. Nothing is wrong with the request: try again later. */
    static class IfscDirectoryUnavailable extends RuntimeException {
        IfscDirectoryUnavailable(Throwable cause) {
            super("IFSC directory unavailable", cause);
        }
    }
}
