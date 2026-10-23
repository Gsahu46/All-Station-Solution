package com.dakroute.shipments;

import com.fasterxml.jackson.annotation.JsonInclude;
import jakarta.validation.ConstraintViolation;
import jakarta.validation.Valid;
import jakarta.validation.Validator;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import org.springframework.dao.DataAccessException;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;

@Service
class BulkShipments {

    /** Demo rule: at most this many shipments in one call. */
    static final int MAX_BATCH = 500;

    record Address(@NotBlank String name, @NotBlank String line1, @NotBlank String city,
                   @NotNull @Pattern(regexp = "[1-9][0-9]{5}", message = "must be 6 digits, not starting with 0") String pincode,
                   @NotNull @Pattern(regexp = "[6-9][0-9]{9}", message = "must be a 10-digit Indian mobile number") String phone) {
    }

    record ShipmentRequest(@NotNull @Pattern(regexp = "[A-Za-z0-9-]{3,40}", message = "must be 3 to 40 letters, digits or dashes") String ref,
                           @NotNull @Pattern(regexp = "[1-9][0-9]{5}", message = "must be 6 digits, not starting with 0") String fromPincode,
                           @NotNull @Valid Address to,
                           @Min(1) @Max(50_000) int weightGrams) {
    }

    record FieldError(String field, String message) {
    }

    @JsonInclude(JsonInclude.Include.NON_NULL)
    record ItemResult(int index, String ref, String status, Long shipmentId, List<FieldError> errors) {
    }

    record Report(int created, int failed, List<ItemResult> results) {
    }

    private final JdbcClient jdbc;
    private final Validator validator;

    BulkShipments(JdbcClient jdbc, Validator validator) {
        this.jdbc = jdbc;
        this.validator = validator;
    }

    /**
     * Each shipment stands alone: it is checked on its own and saved in its own statement, so one bad address fails
     * one item, and the report says which, by its position and the seller's reference.
     */
    Report create(List<ShipmentRequest> items) {
        List<ItemResult> results = new ArrayList<>();
        for (int i = 0; i < items.size(); i++) {
            results.add(createOne(i, items.get(i)));
        }
        int created = (int) results.stream().filter(r -> r.status().equals("created")).count();
        return new Report(created, results.size() - created, results);
    }

    private ItemResult createOne(int index, ShipmentRequest s) {
        if (s == null) {
            return failed(index, null, List.of(new FieldError("", "must not be null")));
        }
        List<FieldError> errors = validator.validate(s).stream()
                .sorted(Comparator.comparing((ConstraintViolation<ShipmentRequest> v) -> v.getPropertyPath().toString()))
                .map(v -> new FieldError(v.getPropertyPath().toString(), v.getMessage())).toList();
        if (!errors.isEmpty()) {
            return failed(index, s.ref(), errors);
        }
        String ref = s.ref().toUpperCase(Locale.ROOT);
        try {
            // One statement, committed on its own: a failure here cannot undo the other items.
            long id = jdbc.sql("""
                            INSERT INTO shipments (ref, from_pincode, to_name, to_line1, to_city, to_pincode, to_phone, weight_grams)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?) RETURNING id""")
                    .params(ref, s.fromPincode(), s.to().name(), s.to().line1(), s.to().city(), s.to().pincode(), s.to().phone(), s.weightGrams())
                    .query(Long.class).single();
            return new ItemResult(index, ref, "created", id, null);
        } catch (DuplicateKeyException e) {
            return failed(index, ref, List.of(new FieldError("ref", "is already used by another shipment")));
        } catch (DataAccessException e) {
            // The database refused it for a reason Java did not check: say so, without passing on SQL details.
            return failed(index, ref, List.of(new FieldError("", "could not be saved")));
        }
    }

    private static ItemResult failed(int index, String ref, List<FieldError> errors) {
        return new ItemResult(index, ref, "failed", null, errors);
    }
}
