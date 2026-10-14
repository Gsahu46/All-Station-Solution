package com.dakroute.partner;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import tools.jackson.databind.PropertyNamingStrategies;
import tools.jackson.databind.annotation.JsonDeserialize;
import tools.jackson.databind.annotation.JsonNaming;

import java.time.Instant;

/**
 * The courier partner's delivery update, exactly as they send it: snake_case names, a local time with no zone,
 * and new fields whenever they like. Only this class is tolerant; the rest of the API stays strict.
 */
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)   // awbNumber <- "awb_number", for this class only
@JsonIgnoreProperties(ignoreUnknown = true)                      // their new fields must not break us
record PartnerUpdate(
        @NotNull @Pattern(regexp = "[A-Za-z0-9]{10,20}", message = "must be 10 to 20 letters and digits") String awbNumber,
        @NotBlank String statusCode,
        /** Challenge 2: "2026-10-14 09:15:00" (India time by contract) or ISO 8601 with an offset (v2). */
        @NotNull @JsonDeserialize(using = PartnerTimeDeserializer.class) Instant eventTime,
        @Valid Location location,
        /** ISO 8601 with an offset, like "2026-10-14T18:00:00+05:30": an exact instant. Optional. */
        Instant promisedBy) {

    @JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
    @JsonIgnoreProperties(ignoreUnknown = true)
    record Location(String cityName, @Pattern(regexp = "\\d{6}", message = "must be a 6-digit PIN code") String pinCode) {
    }
}
