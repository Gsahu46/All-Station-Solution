package com.tijori.loans;

import org.springframework.boot.context.properties.ConfigurationProperties;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.TreeMap;

/** Dated rates from application.yaml (tijori.rates). Each product's list is turned into a TreeMap keyed by start date. */
@ConfigurationProperties("tijori")
record RateTable(Map<Product, List<DatedRate>> rates) {

    record DatedRate(LocalDate from, BigDecimal annualPercent) {
    }

    /** The rate valid on a date: the entry with the latest start date on or before it (TreeMap.floorEntry). */
    Optional<DatedRate> rateOn(Product product, LocalDate date) {
        TreeMap<LocalDate, DatedRate> byStart = new TreeMap<>();
        rates.getOrDefault(product, List.of()).forEach(r -> byStart.put(r.from(), r));
        return Optional.ofNullable(byStart.floorEntry(date)).map(Map.Entry::getValue);
    }
}
