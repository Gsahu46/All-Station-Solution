package com.ghoomo.bookings;

import jakarta.validation.Constraint;
import jakarta.validation.ConstraintValidator;
import jakarta.validation.ConstraintValidatorContext;
import jakarta.validation.Payload;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/** Cross-field: one age per child. */
@Target(ElementType.TYPE)
@Retention(RetentionPolicy.RUNTIME)
@Constraint(validatedBy = ChildAgesMatch.Validator.class)
@interface ChildAgesMatch {

    String message() default "one age per child";

    Class<?>[] groups() default {};

    Class<? extends Payload>[] payload() default {};

    class Validator implements ConstraintValidator<ChildAgesMatch, HotelBookingRequest> {

        @Override
        public boolean isValid(HotelBookingRequest r, ConstraintValidatorContext context) {
            int ages = r.childAges() == null ? 0 : r.childAges().size();
            if (ages == r.childrenOrZero()) {
                return true;
            }
            context.disableDefaultConstraintViolation();
            return ValidStay.Validator.fail(context, "childAges", "give one age for each of the " + r.childrenOrZero() + " children");
        }
    }
}
