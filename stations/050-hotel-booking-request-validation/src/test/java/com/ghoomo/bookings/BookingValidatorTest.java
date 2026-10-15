package com.ghoomo.bookings;

import jakarta.validation.ConstraintViolation;
import jakarta.validation.Validator;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import static org.assertj.core.api.Assertions.assertThat;

/** The validators on their own, through Spring's Validator (so they get the Clock and the catalogue): which group runs what. */
class BookingValidatorTest extends ApiTest {

    @Autowired
    Validator validator;

    static HotelBookingRequest request(int checkInDay, int checkOutDay, int adults, int children) {
        return new HotelBookingRequest(1L, "standard", today().plusDays(checkInDay), today().plusDays(checkOutDay), adults, children, "Asha Verma", "9876543210");
    }

    @Test
    void theDefaultGroupDoesNotLookAcrossFields() {
        assertThat(validator.validate(request(33, 30, 6, 0))).isEmpty();
    }

    @Test
    void theConsistencyGroupReportsEveryProblemOnItsField() {
        assertThat(validator.validate(request(33, 30, 6, 0), Consistency.class))
                .extracting(v -> v.getPropertyPath().toString()).containsExactlyInAnyOrder("checkOut", "guests");
    }

    @Test
    void theMobileValidatorAcceptsCommonWritingsOnly() {
        for (String ok : new String[]{"9876543210", "98765 43210", "+91 98765 43210", "+919876543210", "09876543210", "98765-43210"}) {
            assertThat(IndianMobile.Validator.digits(ok)).as(ok).isEqualTo("9876543210");
        }
        for (String bad : new String[]{"5876543210", "987654321", "98765432100", "+1 9876543210", "98765O4321"}) {
            assertThat(IndianMobile.Validator.digits(bad)).as(bad).isNull();
        }
        assertThat(validator.validate(request(30, 33, 2, 0))).extracting(ConstraintViolation::getMessage).isEmpty();
    }
}
