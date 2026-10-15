package com.tiffino.reports;

import java.time.ZoneId;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/** The report as the spreadsheet macro's replacement first did it, kept only in tests. */
final class OldDailyReport {

    /** A mutable key: equals and hashCode read fields that the loop below keeps changing. */
    static final class OutletHourKey {
        String outlet;
        int hour;

        @Override
        public boolean equals(Object o) {
            return o instanceof OutletHourKey k && k.hour == hour && Objects.equals(k.outlet, outlet);
        }

        @Override
        public int hashCode() {
            return Objects.hash(outlet, hour);
        }
    }

    private OldDailyReport() {
    }

    static Map<OutletHourKey, Double> byOutletHour(List<Sale> sales) {
        Map<OutletHourKey, Double> totals = new HashMap<>();
        OutletHourKey key = new OutletHourKey();   // one object, reused "to save allocations"
        for (Sale s : sales) {
            key.outlet = s.outletId();
            key.hour = s.at().atZone(ZoneId.of("Asia/Kolkata")).getHour();
            totals.merge(key, s.amountRupees().doubleValue(), Double::sum);
        }
        return totals;
    }

    static long outletTotalPaise(List<Sale> sales, String outletId) {
        double rupees = 0;
        for (Sale s : sales) {
            if (s.outletId().equals(outletId)) {
                rupees += s.amountRupees().doubleValue();
            }
        }
        return (long) (rupees * 100);   // 293.9 * 100 is 29389.999999999996 in double
    }
}
