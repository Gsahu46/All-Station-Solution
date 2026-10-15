package com.tiffino.reports;

import java.time.Instant;
import java.util.List;

/** Where sales come from: every sale with from <= at < to. */
interface SalesFeed {
    List<Sale> between(Instant from, Instant to);
}
