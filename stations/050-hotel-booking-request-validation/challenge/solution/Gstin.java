package com.ghoomo.bookings;

import jakarta.validation.Constraint;
import jakarta.validation.ConstraintValidator;
import jakarta.validation.ConstraintValidatorContext;
import jakarta.validation.Payload;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;
import java.util.Locale;

/** A GSTIN's shape and check character. A format check only: it does not prove the GSTIN is registered. */
@Target(ElementType.FIELD)
@Retention(RetentionPolicy.RUNTIME)
@Constraint(validatedBy = Gstin.Validator.class)
@interface Gstin {

    String message() default "must be a 15-character GSTIN with a valid check character";

    Class<?>[] groups() default {};

    Class<? extends Payload>[] payload() default {};

    class Validator implements ConstraintValidator<Gstin, String> {

        private static final String CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ";

        @Override
        public boolean isValid(String value, ConstraintValidatorContext context) {
            if (value == null) {
                return true;   // optional
            }
            String g = value.strip().toUpperCase(Locale.ROOT);
            return g.matches("[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]") && g.charAt(14) == checkCharacter(g);
        }

        /** The first 14 characters, weighted 1 and 2 alternately, base 36. */
        static char checkCharacter(String g) {
            int sum = 0;
            for (int i = 0; i < 14; i++) {
                int product = CHARS.indexOf(g.charAt(i)) * (i % 2 == 0 ? 1 : 2);
                sum += product / 36 + product % 36;
            }
            return CHARS.charAt((36 - sum % 36) % 36);
        }
    }
}
