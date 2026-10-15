package com.ghoomo.bookings;

import jakarta.validation.Constraint;
import jakarta.validation.ConstraintValidator;
import jakarta.validation.ConstraintValidatorContext;
import jakarta.validation.Payload;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/** An Indian mobile number: 10 digits starting 6 to 9, optionally written with +91 or 0, spaces or hyphens. */
@Target(ElementType.FIELD)
@Retention(RetentionPolicy.RUNTIME)
@Constraint(validatedBy = IndianMobile.Validator.class)
@interface IndianMobile {

    String message() default "must be a 10-digit Indian mobile number";

    Class<?>[] groups() default {};

    Class<? extends Payload>[] payload() default {};

    class Validator implements ConstraintValidator<IndianMobile, String> {

        @Override
        public boolean isValid(String value, ConstraintValidatorContext context) {
            return value == null || digits(value) != null;   // null is @NotBlank's job, not this one's
        }

        /** The 10 digits, or null if this is not a mobile number. */
        static String digits(String value) {
            String d = value.replaceAll("[\\s-]", "");
            if (d.startsWith("+91")) {
                d = d.substring(3);
            } else if (d.length() == 11 && d.startsWith("0")) {
                d = d.substring(1);
            }
            return d.matches("[6-9][0-9]{9}") ? d : null;
        }
    }
}
