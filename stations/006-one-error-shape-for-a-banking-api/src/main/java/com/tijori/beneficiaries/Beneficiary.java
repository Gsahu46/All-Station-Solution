package com.tijori.beneficiaries;

import java.time.Instant;
import java.util.UUID;

/** A stored beneficiary. The full account number stays inside the app; responses show only the last 4 digits. */
record Beneficiary(UUID id, String owner, String name, String accountNumber, String ifsc, String bankBranch, Instant createdAt) {

    BeneficiaryView view() {
        String masked = "X".repeat(accountNumber.length() - 4) + accountNumber.substring(accountNumber.length() - 4);
        return new BeneficiaryView(id, name, masked, ifsc, bankBranch, createdAt);
    }
}
