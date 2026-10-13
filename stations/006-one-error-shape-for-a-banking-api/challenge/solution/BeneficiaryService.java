package com.tijori.beneficiaries;

import org.springframework.stereotype.Service;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.Optional;
import java.util.UUID;

/** The rules. It throws business exceptions and knows nothing about HTTP. */
@Service
class BeneficiaryService {

    private final IfscDirectory directory;
    private final BeneficiaryStore store;

    BeneficiaryService(IfscDirectory directory, BeneficiaryStore store) {
        this.directory = directory;
        this.store = store;
    }

    /** synchronized: the duplicate check and the save must not interleave with another request from the same customer. */
    synchronized BeneficiaryView add(String owner, BeneficiaryRequest r) {
        Optional<String> found;
        try {
            found = directory.branch(r.ifsc());
        } catch (RuntimeException e) {
            throw new Exceptions.IfscDirectoryUnavailable(e); // an outage is not the customer's mistake: 503, not 400
        }
        String branch = found.orElseThrow(Exceptions.UnknownIfsc::new);
        store.findSame(owner, r.accountNumber(), r.ifsc()).ifPresent(existing -> {
            throw new Exceptions.DuplicateBeneficiary(existing.id());
        });
        var b = new Beneficiary(UUID.randomUUID(), owner, r.name(), r.accountNumber(), r.ifsc(), branch,
                Instant.now().truncatedTo(ChronoUnit.MILLIS));
        return store.save(b).view();
    }

    /** Challenge 1: the same ownership rule as get(), so deleting someone else's is "not found" too. */
    void delete(String owner, UUID id) {
        get(owner, id);
        store.delete(id);
    }

    /** Another customer's beneficiary is "not found", exactly like one that does not exist. */
    BeneficiaryView get(String owner, UUID id) {
        return store.find(id)
                .filter(b -> b.owner().equals(owner))
                .orElseThrow(() -> new Exceptions.BeneficiaryNotFound(id))
                .view();
    }
}
