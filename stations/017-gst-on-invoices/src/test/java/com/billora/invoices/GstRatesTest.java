package com.billora.invoices;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.Random;
import java.util.stream.IntStream;

import static org.assertj.core.api.Assertions.assertThat;

/** The configured rates on their boundary days and prices, and the rounding bound on generated invoices. */
@SpringBootTest
class GstRatesTest {

    static final LocalDate BEFORE = LocalDate.of(2025, 9, 21);
    static final LocalDate FROM = LocalDate.of(2025, 9, 22);

    @Autowired
    GstRates rates;

    BigDecimal tShirt(LocalDate date, long paise) {
        return rates.rate("6109", date, paise).orElseThrow();
    }

    @Test
    void tShirtSlabsByPricePerPieceAndDate() {
        assertThat(tShirt(BEFORE, 100_000)).isEqualByComparingTo("5");     // Rs 1,000: not above the slab
        assertThat(tShirt(BEFORE, 100_001)).isEqualByComparingTo("12");
        assertThat(tShirt(FROM, 100_001)).isEqualByComparingTo("5");       // the slab moved to Rs 2,500
        assertThat(tShirt(FROM, 250_000)).isEqualByComparingTo("5");
        assertThat(tShirt(FROM, 250_001)).isEqualByComparingTo("18");
    }

    @Test
    void noRateBeforeGstOrForAnUnknownHeading() {
        assertThat(rates.rate("8471", LocalDate.of(2017, 6, 30), 100)).isEmpty();
        assertThat(rates.rate("8471", LocalDate.of(2017, 7, 1), 100)).isPresent();
        assertThat(rates.rate("9999", FROM, 100)).isEmpty();
    }

    @Test
    void roundingOncePerRateIsWithinHalfAPaisaPerTaxHead() {
        Random random = new Random(17);
        for (int i = 0; i < 1_000; i++) {
            var lines = IntStream.range(0, 1 + random.nextInt(20)).mapToObj(n -> new Gst.PricedLine(n + 1, "x", "8471", 1, 1,
                    1 + random.nextInt(1_000_000), BigDecimal.valueOf(new int[]{5, 12, 18, 28}[random.nextInt(4)]))).toList();
            for (Gst.SupplyType type : Gst.SupplyType.values()) {
                for (Gst.RateTotal t : Gst.summary(lines, type)) {
                    BigDecimal exact = BigDecimal.valueOf(t.taxableValuePaise()).multiply(t.ratePercent()).movePointLeft(2);
                    long charged = t.cgstPaise() + t.sgstPaise() + t.igstPaise();
                    assertThat(exact.subtract(BigDecimal.valueOf(charged)).abs()).isLessThanOrEqualTo(BigDecimal.ONE);   // two halves at most
                    assertThat(t.cgstPaise()).isEqualTo(t.sgstPaise());
                }
            }
        }
    }
}
