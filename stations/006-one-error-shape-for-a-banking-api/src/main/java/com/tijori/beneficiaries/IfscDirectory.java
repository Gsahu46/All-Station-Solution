package com.tijori.beneficiaries;

import org.springframework.stereotype.Component;

import java.util.Map;
import java.util.Optional;

/**
 * Looks up a bank branch by IFSC. Simulated: a fixed list instead of the real directory service. A real lookup
 * is a network call that can fail; callers must treat that failure (IfscDirectoryUnavailable) differently from
 * "no such IFSC" (an empty Optional).
 */
@Component
class IfscDirectory {

    private final Map<String, String> branches = Map.of(
            "HDFC0001234", "HDFC Bank, Koramangala, Bengaluru",
            "SBIN0005943", "State Bank of India, Andheri West, Mumbai",
            "ICIC0000456", "ICICI Bank, Salt Lake, Kolkata",
            "UTIB0000789", "Axis Bank, Banjara Hills, Hyderabad");

    Optional<String> branch(String ifsc) {
        return Optional.ofNullable(branches.get(ifsc));
    }
}
