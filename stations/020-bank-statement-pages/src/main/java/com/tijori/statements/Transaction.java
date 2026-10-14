package com.tijori.statements;

import java.time.LocalDateTime;

/** A statement line. Negative amounts are debits. Times are in IST. */
record Transaction(long id, LocalDateTime postedAt, String description, long amountPaise) implements Page.Identified {
}
