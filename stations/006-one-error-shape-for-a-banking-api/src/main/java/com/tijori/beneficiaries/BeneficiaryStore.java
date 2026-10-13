package com.tijori.beneficiaries;

import org.springframework.stereotype.Component;

import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/** Beneficiaries in memory (lost on restart). A database comes in later stations. */
@Component
class BeneficiaryStore {

    private final Map<UUID, Beneficiary> byId = new ConcurrentHashMap<>();

    Beneficiary save(Beneficiary b) {
        byId.put(b.id(), b);
        return b;
    }

    Optional<Beneficiary> find(UUID id) {
        return Optional.ofNullable(byId.get(id));
    }

    Optional<Beneficiary> findSame(String owner, String accountNumber, String ifsc) {
        return byId.values().stream()
                .filter(b -> b.owner().equals(owner) && b.accountNumber().equals(accountNumber) && b.ifsc().equals(ifsc))
                .findFirst();
    }
}
