package com.billora.invoices;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import java.time.LocalDate;
import java.util.List;

record TaxPreviewRequest(@NotNull LocalDate invoiceDate,
                         @NotNull @Pattern(regexp = "\\d{2}", message = "must be a two-digit GST state code") String placeOfSupply,
                         @NotEmpty @Size(max = 100) List<@Valid @NotNull Line> lines) {

    record Line(@NotBlank @Size(max = 80) String description,
                @NotNull @Pattern(regexp = "\\d{4}", message = "must be a 4-digit HSN heading (a demo rule)") String hsn,
                @NotNull @Min(1) @Max(10_000) Integer quantity,
                @NotNull @Min(1) @Max(value = 100_000_000, message = "must be at most Rs 10,00,000 a piece (a demo rule)") Long unitPricePaise) {
    }
}
