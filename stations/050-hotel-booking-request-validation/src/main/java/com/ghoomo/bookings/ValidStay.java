package com.ghoomo.bookings;

import jakarta.validation.Constraint;
import jakarta.validation.ConstraintValidator;
import jakarta.validation.ConstraintValidatorContext;
import jakarta.validation.Payload;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;
import java.time.Clock;
import java.time.LocalDate;
import java.time.temporal.ChronoUnit;

/**
 * Cross-field: the stay makes sense as a whole. Check-in today or later and at most a year ahead; check-out after
 * check-in; at most 30 nights. Demo rules. A class-level constraint, because no single field can see the other.
 */
@Target(ElementType.TYPE)
@Retention(RetentionPolicy.RUNTIME)
@Constraint(validatedBy = ValidStay.Validator.class)
@interface ValidStay {

    int MAX_NIGHTS = 30;
    int MAX_DAYS_AHEAD = 365;

    String message() default "the stay is not possible";

    Class<?>[] groups() default {};

    Class<? extends Payload>[] payload() default {};

    /** Created by Spring, so it can be given the Clock like any other bean. */
    class Validator implements ConstraintValidator<ValidStay, HotelBookingRequest> {

        private final Clock clock;

        Validator(Clock clock) {
            this.clock = clock;
        }

        @Override
        public boolean isValid(HotelBookingRequest r, ConstraintValidatorContext context) {
            if (r.checkIn() == null || r.checkOut() == null) {
                return true;   // a missing date is a field error (400), reported by @NotNull
            }
            context.disableDefaultConstraintViolation();
            LocalDate today = LocalDate.now(clock);
            boolean ok = true;
            if (r.checkIn().isBefore(today)) {
                ok = fail(context, "checkIn", "must be today (" + today + ") or later");
            } else if (r.checkIn().isAfter(today.plusDays(MAX_DAYS_AHEAD))) {
                ok = fail(context, "checkIn", "bookings open at most " + MAX_DAYS_AHEAD + " days ahead");
            }
            if (!r.checkOut().isAfter(r.checkIn())) {
                ok = fail(context, "checkOut", "must be after checkIn: a stay is at least one night");
            } else if (ChronoUnit.DAYS.between(r.checkIn(), r.checkOut()) > MAX_NIGHTS) {
                ok = fail(context, "checkOut", "a stay is at most " + MAX_NIGHTS + " nights");
            }
            return ok;
        }

        static boolean fail(ConstraintValidatorContext context, String field, String message) {
            context.buildConstraintViolationWithTemplate(message).addPropertyNode(field).addConstraintViolation();
            return false;
        }
    }
}
