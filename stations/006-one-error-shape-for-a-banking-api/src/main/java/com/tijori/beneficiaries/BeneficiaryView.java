package com.tijori.beneficiaries;

import java.time.Instant;
import java.util.UUID;

/** The response body. */
public record BeneficiaryView(UUID id, String name, String accountNumberMasked, String ifsc, String bankBranch, Instant createdAt) {
}
