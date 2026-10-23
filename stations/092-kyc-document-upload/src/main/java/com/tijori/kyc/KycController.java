package com.tijori.kyc;

import org.springframework.http.HttpStatus;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.io.InputStream;
import java.util.List;
import java.util.Map;
import java.util.Set;

@RestController
class KycController {

    static final Set<String> TYPES = Set.of("PAN", "PASSPORT", "DRIVING_LICENCE", "VOTER_ID");
    /** Demo customers: sign-in name to customer id. */
    static final Map<String, Long> CUSTOMERS = Map.of("asha", 1L, "rohan", 2L);

    private final DocumentStore store;

    KycController(DocumentStore store) {
        this.store = store;
    }

    /** A customer uploads their own document. The file part is streamed to storage; its name and type header are not trusted. */
    @PostMapping("/kyc/{customerId}/documents")
    @ResponseStatus(HttpStatus.CREATED)
    DocumentStore.Document upload(@PathVariable long customerId, @RequestParam String type, @RequestPart("file") MultipartFile file, Authentication who) throws IOException {
        if (!CUSTOMERS.get(who.getName()).equals(customerId)) {
            throw new AccessDeniedException("not this customer's documents");
        }
        if (!TYPES.contains(type)) {
            throw DocumentStore.problem(HttpStatus.BAD_REQUEST, "type must be one of PAN, PASSPORT, DRIVING_LICENCE, VOTER_ID");
        }
        try (InputStream in = file.getInputStream()) {
            return store.store(customerId, type, file.getOriginalFilename(), in);
        }
    }

    /** A customer sees their own documents; a KYC reviewer sees any customer's. */
    @GetMapping("/kyc/{customerId}/documents")
    List<DocumentStore.Document> list(@PathVariable long customerId, Authentication who) {
        boolean reviewer = who.getAuthorities().stream().anyMatch(a -> a.getAuthority().equals("ROLE_REVIEWER"));
        if (!reviewer && !Long.valueOf(customerId).equals(CUSTOMERS.get(who.getName()))) {
            throw new AccessDeniedException("not this customer's documents");
        }
        if (!CUSTOMERS.containsValue(customerId)) {
            throw DocumentStore.problem(HttpStatus.NOT_FOUND, "No such customer");
        }
        return store.list(customerId);
    }
}
