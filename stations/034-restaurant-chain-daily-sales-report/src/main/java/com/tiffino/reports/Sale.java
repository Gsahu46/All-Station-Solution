package com.tiffino.reports;

import java.math.BigDecimal;
import java.time.Instant;

/** One bill from an outlet's till. The till exports rupees as decimal text ("261.45"), read exactly as BigDecimal. */
record Sale(String outletId, Instant at, BigDecimal amountRupees) {
}
