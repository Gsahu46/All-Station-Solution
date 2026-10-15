package com.basketo.delivery;

import jakarta.validation.Valid;
import jakarta.validation.constraints.AssertTrue;
import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.validation.annotation.Validated;

import java.util.List;
import java.util.Map;

/**
 * Per-city delivery settings from configuration (basketo.cities.*), checked when the app starts. A typo in a key,
 * a missing value or a minimum order of zero stops the app from starting, instead of quietly taking orders at Rs 0.
 * Wrapper types (Long, Double), not primitives: a missing value is null and fails @NotNull, never a silent 0.
 */
@ConfigurationProperties(prefix = "basketo", ignoreUnknownFields = false)
@Validated
record DeliverySettings(@NotEmpty Map<String, @Valid @NotNull City> cities) {

    record City(@NotNull @DecimalMin("0.5") @DecimalMax("15.0") Double radiusKm,
                @NotNull @Min(0) @Max(10_000) Long feePaise,
                @NotNull @Min(value = 9_900, message = "must be at least 9900 paise (Rs 99): a demo floor") Long minimumOrderPaise,
                @NotNull @Valid Location store,
                @Min(1) Long freeDeliveryAbovePaise,
                List<@Valid @NotNull FeeBand> feeBands) {

        /** Challenge 1: a rule across two fields. Checked by validation because the method starts with "is". */
        @AssertTrue(message = "free-delivery-above-paise must be above minimum-order-paise")
        public boolean isFreeDeliveryAboveMinimum() {
            return freeDeliveryAbovePaise == null || minimumOrderPaise == null || freeDeliveryAbovePaise > minimumOrderPaise;
        }

        /** Challenge 2: bands in increasing distance, the last one reaching the radius. */
        @AssertTrue(message = "fee-bands must increase and the last must reach radius-km")
        public boolean isFeeBandsCoverTheRadius() {
            if (feeBands == null || feeBands.isEmpty()) {
                return true;
            }
            for (int i = 1; i < feeBands.size(); i++) {
                if (feeBands.get(i).upToKm() <= feeBands.get(i - 1).upToKm()) {
                    return false;
                }
            }
            return radiusKm == null || feeBands.getLast().upToKm() >= radiusKm;
        }

        /** The fee for an order at this distance: banded if bands are set, free above the threshold. */
        long feeFor(double km, long orderPaise) {
            if (freeDeliveryAbovePaise != null && orderPaise >= freeDeliveryAbovePaise) {
                return 0;
            }
            if (feeBands == null || feeBands.isEmpty()) {
                return feePaise;
            }
            return feeBands.stream().filter(b -> km <= b.upToKm()).findFirst().orElse(feeBands.getLast()).feePaise();
        }
    }

    /** Challenge 2: one band, "up to this many km, this fee". */
    record FeeBand(@NotNull @DecimalMin("0.1") Double upToKm, @NotNull @Min(0) Long feePaise) {
    }

    record Location(@NotNull @DecimalMin("-90") @DecimalMax("90") Double lat, @NotNull @DecimalMin("-180") @DecimalMax("180") Double lon) {
    }
}
