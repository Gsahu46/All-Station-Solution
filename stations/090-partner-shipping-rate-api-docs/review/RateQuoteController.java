package com.dakroute.rates;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.util.concurrent.atomic.AtomicLong;

/**
 * The partner docs are generated from this code: the paths, the fields with their limits (from the validation
 * annotations), the errors and the examples. Every example here is sent to the API by a test, so it cannot drift.
 */
@RestController
class RateQuoteController {

        @Schema(description = "A parcel to price.")
    record QuoteRequest(
            @Schema(description = "Pickup PIN code: six digits, not starting with 0.", example = "560001")
            @NotNull @Pattern(regexp = "[1-9][0-9]{5}") String fromPincode,
            @Schema(description = "Delivery PIN code.", example = "110001")
            @NotNull @Pattern(regexp = "[1-9][0-9]{5}") String toPincode,
            @Schema(description = "Actual weight in grams. Above 50,000 g the parcel service cannot carry it (422).", example = "1200")
            @Min(1) int weightGrams,
            @Schema(description = "Length in cm.", example = "30") @Min(1) @Max(150) int lengthCm,
            @Schema(description = "Width in cm.", example = "20") @Min(1) @Max(150) int widthCm,
            @Schema(description = "Height in cm.", example = "10") @Min(1) @Max(150) int heightCm,
            @Schema(description = "STANDARD or EXPRESS.", example = "STANDARD") @NotNull RateCard.Service service) {
    }

    @Schema(description = "A price for one parcel. Amounts are integer paise (₹1 = 100 paise).")
    record Quote(@Schema(example = "Q-1") String quoteId, RateCard.Zone zone,
                 @Schema(description = "The larger of actual and volumetric weight.") long chargeableWeightGrams,
                 long pricePaise, @Schema(description = "GST at 18%.") long gstPaise, long totalPaise,
                 @Schema(description = "Working days, a demo estimate.") int estimatedDays) {
    }

    static final String PARCEL = """
            {"fromPincode": "560001", "toPincode": "110001", "weightGrams": 1200, "lengthCm": 30, "widthCm": 20, "heightCm": 10, "service": "STANDARD"}""";
    static final String PARCEL_QUOTE = """
            {"quoteId": "Q-1", "zone": "NATIONAL", "chargeableWeightGrams": 1200, "pricePaise": 22500, "gstPaise": 4050, "totalPaise": 26550, "estimatedDays": 5}""";
    static final String LIGHT_BUT_BULKY = """
            {"fromPincode": "560001", "toPincode": "560034", "weightGrams": 800, "lengthCm": 60, "widthCm": 40, "heightCm": 40, "service": "EXPRESS"}""";
    static final String TOO_HEAVY = """
            {"fromPincode": "560001", "toPincode": "110001", "weightGrams": 62000, "lengthCm": 80, "widthCm": 60, "heightCm": 60, "service": "STANDARD"}""";
    static final String BAD_PINCODE = """
            {"fromPincode": "56001", "toPincode": "110001", "weightGrams": 1200, "lengthCm": 30, "widthCm": 20, "heightCm": 10, "service": "STANDARD"}""";

    private final AtomicLong quotes = new AtomicLong();

    // springdoc generates the docs from the method anyway: no need for all those annotations.
    @PostMapping("/rate-quotes")
    Quote quote(@Valid @RequestBody QuoteRequest r) {
        if (r.weightGrams() > RateCard.MAX_WEIGHT_GRAMS) {
            // A weight we cannot carry is a bad request like any other invalid input.
            throw new ErrorResponseException(HttpStatus.BAD_REQUEST, ProblemDetail.forStatusAndDetail(HttpStatus.BAD_REQUEST, "Parcels above " + RateCard.MAX_WEIGHT_GRAMS + " g cannot be carried"), null);
        }
        if (RateCard.NOT_SERVED.contains(r.fromPincode()) || RateCard.NOT_SERVED.contains(r.toPincode())) {
            throw unprocessable("This PIN code is not served yet");
        }
        RateCard.Zone zone = RateCard.zone(r.fromPincode(), r.toPincode());
        long chargeable = Math.max(r.weightGrams(), RateCard.volumetricGrams(r.lengthCm(), r.widthCm(), r.heightCm()));
        long price = RateCard.pricePaise(zone, r.service(), chargeable);
        long gst = RateCard.gstPaise(price);
        return new Quote("Q-" + quotes.incrementAndGet(), zone, chargeable, price, gst, price + gst, RateCard.days(zone, r.service()));
    }

    private static ErrorResponseException unprocessable(String detail) {
        return new ErrorResponseException(HttpStatus.UNPROCESSABLE_CONTENT, ProblemDetail.forStatusAndDetail(HttpStatus.UNPROCESSABLE_CONTENT, detail), null);
    }
}
