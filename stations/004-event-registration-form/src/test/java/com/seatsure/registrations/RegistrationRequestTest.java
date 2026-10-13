package com.seatsure.registrations;

import jakarta.validation.Validation;
import jakarta.validation.Validator;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/** The validation rules on their own, without Spring or HTTP: boundaries, and what @Email does and does not check. */
class RegistrationRequestTest {

    private final Validator validator = Validation.buildDefaultValidatorFactory().getValidator();

    private boolean valid(String name, String email, String phone, Integer tickets) {
        return validator.validate(new RegistrationRequest(name, email, phone, tickets)).isEmpty();
    }

    @Test
    void ticketsFrom1To10() {
        assertThat(valid("Asha", "asha@example.com", null, 1)).isTrue();
        assertThat(valid("Asha", "asha@example.com", null, 10)).isTrue();
        assertThat(valid("Asha", "asha@example.com", null, 0)).isFalse();
        assertThat(valid("Asha", "asha@example.com", null, 11)).isFalse();
        assertThat(valid("Asha", "asha@example.com", null, -3)).isFalse();
    }

    @Test
    void phoneIsOptionalButMustBeAMobileNumberWhenGiven() {
        assertThat(valid("Asha", "asha@example.com", null, 1)).isTrue();
        assertThat(valid("Asha", "asha@example.com", "6000000000", 1)).isTrue();
        assertThat(valid("Asha", "asha@example.com", "5876543210", 1)).isFalse();   // starts with 5
        assertThat(valid("Asha", "asha@example.com", "+919876543210", 1)).isFalse(); // country code: not accepted here
    }

    @Test
    void nameLongerThan100IsRejected() {
        assertThat(valid("A".repeat(100), "asha@example.com", null, 1)).isTrue();
        assertThat(valid("A".repeat(101), "asha@example.com", null, 1)).isFalse();
    }

    @Test
    void emailChecksTheShapeNotThatTheAddressExists() {
        assertThat(valid("Asha", "asha", null, 1)).isFalse();
        assertThat(valid("Asha", "asha@@example.com", null, 1)).isFalse();
        // @Email accepts a domain without a dot. Valid by the email rules, but it is not proof the address works:
        // only a confirmation email proves that.
        assertThat(valid("Asha", "asha@localhost", null, 1)).isTrue();
    }
}
