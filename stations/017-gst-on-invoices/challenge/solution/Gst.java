package com.billora.invoices;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/** The tax arithmetic. Tax is computed per rate on the invoice's taxable total and rounded once, to the paisa. */
final class Gst {

    enum SupplyType { INTRA_STATE, INTER_STATE }

    record PricedLine(int line, String description, String hsn, int quantity, long unitPricePaise,
                      long taxableValuePaise, BigDecimal ratePercent, long discountPaise) {

        PricedLine(int line, String description, String hsn, int quantity, long unitPricePaise, long taxableValuePaise, BigDecimal ratePercent) {
            this(line, description, hsn, quantity, unitPricePaise, taxableValuePaise, ratePercent, 0);
        }
    }

    record RateTotal(BigDecimal ratePercent, long taxableValuePaise, long cgstPaise, long sgstPaise, long igstPaise, long utgstPaise) {
    }

    private Gst() {
    }

    /** Same state: half the rate as CGST (to the Centre) and half as SGST (to the state). Different states: IGST. */
    static SupplyType supplyType(GstState seller, GstState placeOfSupply) {
        return seller == placeOfSupply ? SupplyType.INTRA_STATE : SupplyType.INTER_STATE;
    }

    /** One row per rate. A TreeMap keyed by BigDecimal compares with compareTo, so 18 and 18.00 are the same rate. */
    static List<RateTotal> summary(List<PricedLine> lines, SupplyType type) {
        return summary(lines, type, false);
    }

    /** Challenge 2: inside one union territory the second half is UTGST instead of SGST. */
    static List<RateTotal> summary(List<PricedLine> lines, SupplyType type, boolean unionTerritory) {
        Map<BigDecimal, Long> taxableByRate = new TreeMap<>();
        lines.forEach(l -> taxableByRate.merge(l.ratePercent(), l.taxableValuePaise(), Long::sum));
        List<RateTotal> totals = new ArrayList<>();
        taxableByRate.forEach((rate, taxable) -> {
            if (type == SupplyType.INTRA_STATE) {
                long half = percentOf(taxable, rate.divide(BigDecimal.TWO));
                totals.add(unionTerritory ? new RateTotal(rate, taxable, half, 0, 0, half) : new RateTotal(rate, taxable, half, half, 0, 0));
            } else {
                totals.add(new RateTotal(rate, taxable, 0, 0, percentOf(taxable, rate), 0));
            }
        });
        return totals;
    }

    /** taxable x percent / 100, rounded half up to the paisa. Exact until that one rounding. */
    static long percentOf(long paise, BigDecimal percent) {
        return BigDecimal.valueOf(paise).multiply(percent).movePointLeft(2).setScale(0, RoundingMode.HALF_UP).longValueExact();
    }
}
