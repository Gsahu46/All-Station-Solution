package com.tijori.profiles;

import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * Two demo customers in memory. Every number is made up (the card numbers are the well-known test numbers), and
 * no CVV is stored anywhere: card rules forbid keeping it after authorisation.
 */
@Component
class Customers {

    record Card(String network, Sensitive number, String expiry) {
    }

    record Profile(String customerId, String name, Sensitive mobile, Sensitive email, Sensitive aadhaar,
                   List<Card> cards, Sensitive bankAccount) {
    }

    private final Map<String, Profile> profiles = Map.of(
            "c-1001", new Profile("c-1001", "Asha Rao", Sensitive.mobile("9876543210"), Sensitive.email("asha.rao@example.com"),
                    Sensitive.aadhaar("234567890123"),
                    List.of(new Card("VISA", Sensitive.card("4111111111111111"), "08/29")),
                    Sensitive.account("50100012345678")),
            "c-1002", new Profile("c-1002", "Ravi Kumar", Sensitive.mobile("9123456780"), Sensitive.email("ravi@example.com"),
                    Sensitive.aadhaar("345678901234"),
                    List.of(new Card("MASTERCARD", Sensitive.card("5555555555554444"), "01/28"),
                            new Card("VISA", Sensitive.card("4012888888881881"), "11/27")),
                    Sensitive.account("00011122233344")));

    /** Which customer each demo sign-in is. */
    private final Map<String, String> customerOfUser = Map.of("asha", "c-1001", "ravi", "c-1002");

    Optional<Profile> profile(String customerId) {
        return Optional.ofNullable(profiles.get(customerId));
    }

    Optional<String> customerOf(String username) {
        return Optional.ofNullable(customerOfUser.get(username));
    }
}
