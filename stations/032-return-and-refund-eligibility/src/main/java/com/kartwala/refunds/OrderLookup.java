package com.kartwala.refunds;

import java.util.Optional;

/** Where orders come from. A query: tests stub it. */
interface OrderLookup {
    Optional<Order> find(String orderId);
}
