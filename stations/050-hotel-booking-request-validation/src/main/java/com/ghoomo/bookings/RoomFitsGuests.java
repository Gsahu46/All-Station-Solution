package com.ghoomo.bookings;

import jakarta.validation.Constraint;
import jakarta.validation.ConstraintValidator;
import jakarta.validation.ConstraintValidatorContext;
import jakarta.validation.Payload;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;
import java.util.TreeSet;

/** Cross-field and catalogue: the hotel exists, has this room type, and the room sleeps everyone (adults + children). */
@Target(ElementType.TYPE)
@Retention(RetentionPolicy.RUNTIME)
@Constraint(validatedBy = RoomFitsGuests.Validator.class)
@interface RoomFitsGuests {

    String message() default "the room does not fit the guests";

    Class<?>[] groups() default {};

    Class<? extends Payload>[] payload() default {};

    /** Created by Spring, so it can use the catalogue bean. */
    class Validator implements ConstraintValidator<RoomFitsGuests, HotelBookingRequest> {

        private final HotelCatalog catalog;

        Validator(HotelCatalog catalog) {
            this.catalog = catalog;
        }

        @Override
        public boolean isValid(HotelBookingRequest r, ConstraintValidatorContext context) {
            if (r.hotelId() == null || r.roomType() == null || r.adults() == null) {
                return true;   // missing fields are reported by the Default group (400)
            }
            context.disableDefaultConstraintViolation();
            HotelCatalog.Hotel hotel = catalog.find(r.hotelId()).orElse(null);
            if (hotel == null) {
                return ValidStay.Validator.fail(context, "hotelId", "no hotel " + r.hotelId());
            }
            Integer sleeps = hotel.sleeps().get(HotelCatalog.roomType(r.roomType()));
            if (sleeps == null) {
                return ValidStay.Validator.fail(context, "roomType", hotel.name() + " has no such room type; it has " + new TreeSet<>(hotel.sleeps().keySet()));
            }
            int guests = r.adults() + r.childrenOrZero();
            if (guests > sleeps) {
                return ValidStay.Validator.fail(context, "guests", guests + " guests do not fit a " + HotelCatalog.roomType(r.roomType()) + " room, which sleeps " + sleeps);
            }
            return true;
        }
    }
}
