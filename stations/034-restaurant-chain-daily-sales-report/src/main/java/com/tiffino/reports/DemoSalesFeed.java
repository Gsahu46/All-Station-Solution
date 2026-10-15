package com.tiffino.reports;

import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Clock;
import java.time.Instant;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Random;

/**
 * Demo sales for the 7 days before today, generated at startup with fixed seeds, so a given day's report reads the
 * same whenever the app is started. Menu prices plus 5% GST, rounded to the paisa, as a till would print them.
 */
@Component
class DemoSalesFeed implements SalesFeed {

    private static final int[] MENU = {89, 129, 149, 179, 199, 249, 299, 349};
    private static final BigDecimal WITH_GST = new BigDecimal("1.05");

    private final List<Sale> sales = new ArrayList<>();

    DemoSalesFeed(Clock clock, Outlets outlets) {
        LocalDate today = DailySalesReport.today(clock);
        for (int daysAgo = 1; daysAgo <= 7; daysAgo++) {
            Random random = new Random(1_000L + daysAgo);   // same seed for "yesterday" every time
            LocalDate day = today.minusDays(daysAgo);
            for (String outlet : outlets.ids()) {
                int bills = 20 + random.nextInt(30);
                for (int b = 0; b < bills; b++) {
                    Instant at = day.atTime(8 + random.nextInt(15), random.nextInt(60)).atZone(DailySalesReport.INDIA).toInstant();
                    int items = 1 + random.nextInt(3);
                    int rupees = 0;
                    for (int i = 0; i < items; i++) {
                        rupees += MENU[random.nextInt(MENU.length)];
                    }
                    sales.add(new Sale(outlet, at, BigDecimal.valueOf(rupees).multiply(WITH_GST).setScale(2, RoundingMode.HALF_UP)));
                }
            }
        }
        sales.sort(Comparator.comparing(Sale::at));
    }

    @Override
    public List<Sale> between(Instant from, Instant to) {
        return sales.stream().filter(s -> !s.at().isBefore(from) && s.at().isBefore(to)).toList();
    }
}
