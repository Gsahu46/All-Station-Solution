package com.basketo.delivery;

import jakarta.validation.Valid;
import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.validation.annotation.Validated;

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
                @NotNull @Valid Location store) {
    }

    record Location(@NotNull @DecimalMin("-90") @DecimalMax("90") Double lat, @NotNull @DecimalMin("-180") @DecimalMax("180") Double lon) {
    }
}
