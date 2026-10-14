package com.billora.invoices;

import org.springframework.boot.context.properties.ConfigurationProperties;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.TreeMap;

/**
 * GST rates by HSN heading from application.yaml (billora.hsn-rates). Each heading has dated rate sets; each set has
 * value slabs (some goods are taxed by price per piece). Two lookups, both "the latest start on or before":
 * the set valid on the invoice date, then the slab for the unit price.
 */
@ConfigurationProperties("billora")
record GstRates(GstState sellerState, Map<String, List<DatedSlabs>> hsnRates) {

    record DatedSlabs(LocalDate from, List<Slab> slabs) {
    }

    /** A slab starts at fromPaise per piece (inclusive) and runs until the next slab starts. */
    record Slab(long fromPaise, BigDecimal percent) {
    }

    Optional<BigDecimal> rate(String hsn, LocalDate invoiceDate, long unitPricePaise) {
        TreeMap<LocalDate, DatedSlabs> byDate = new TreeMap<>();
        hsnRates.getOrDefault(hsn, List.of()).forEach(d -> byDate.put(d.from(), d));
        return Optional.ofNullable(byDate.floorEntry(invoiceDate)).map(e -> {
            TreeMap<Long, BigDecimal> byPrice = new TreeMap<>();
            e.getValue().slabs().forEach(s -> byPrice.put(s.fromPaise(), s.percent()));
            return byPrice.floorEntry(unitPricePaise).getValue();
        });
    }
}
