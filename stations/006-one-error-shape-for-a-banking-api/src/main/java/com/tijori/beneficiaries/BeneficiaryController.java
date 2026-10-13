package com.tijori.beneficiaries;

import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.net.URI;
import java.security.Principal;
import java.util.UUID;

/** No try/catch here: every failure is an exception, and ApiErrors turns each one into the same problem shape. */
@RestController
@RequestMapping("/beneficiaries")
class BeneficiaryController {

    private final BeneficiaryService service;

    BeneficiaryController(BeneficiaryService service) {
        this.service = service;
    }

    /** The owner is the signed-in customer, never a field in the body. */
    @PostMapping
    ResponseEntity<BeneficiaryView> add(Principal customer, @Valid @RequestBody BeneficiaryRequest request) {
        BeneficiaryView saved = service.add(customer.getName(), request);
        return ResponseEntity.created(URI.create("/beneficiaries/" + saved.id())).body(saved);
    }

    @GetMapping("/{id}")
    BeneficiaryView get(Principal customer, @PathVariable UUID id) {
        return service.get(customer.getName(), id);
    }
}
