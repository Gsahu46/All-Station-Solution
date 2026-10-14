package com.tijori.statements;

import org.springframework.stereotype.Component;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Random;

/**
 * Two demo accounts in memory: acc-1001 with 4,000 generated transactions from a fixed seed (the same every run),
 * and acc-1002 with none. Each list is kept in statement order.
 */
@Component
class Accounts {

    /** Newest first; transactions posted at the same minute (batch postings) are ordered by id, newest first. */
    static final Comparator<Transaction> STATEMENT_ORDER =
            Comparator.comparing(Transaction::postedAt).reversed().thenComparing(Transaction::id, Comparator.reverseOrder());

    private static final String[] DEBITS = {"UPI to grocer", "Card at fuel station", "ATM withdrawal", "UPI to pharmacy", "NEFT rent", "Electricity bill"};
    private static final LocalTime[] BATCH_TIMES = {LocalTime.of(0, 0), LocalTime.of(9, 30), LocalTime.of(13, 15), LocalTime.of(18, 45)};

    private final Map<String, List<Transaction>> statements = Map.of("acc-1001", generate(4_000), "acc-1002", List.of());

    Optional<List<Transaction>> statement(String accountId) {
        return Optional.ofNullable(statements.get(accountId));
    }

    /** Ids grow day by day; within a day the posting minute is random and up to 19 rows share one, so order needs a tie-breaker. */
    static List<Transaction> generate(int count) {
        Random random = new Random(20);
        List<Transaction> all = new ArrayList<>(count);
        LocalDate day = LocalDate.of(2025, 10, 1);
        for (long id = 1; id <= count; id++) {
            if (random.nextInt(11) == 0) {
                day = day.plusDays(1);
            }
            LocalDateTime at = day.atTime(BATCH_TIMES[random.nextInt(BATCH_TIMES.length)]);
            boolean credit = random.nextInt(10) == 0;
            all.add(credit
                    ? new Transaction(id, at, "Salary or refund credit", 100_000 + random.nextInt(5_000_000))
                    : new Transaction(id, at, DEBITS[random.nextInt(DEBITS.length)], -(5_000 + random.nextInt(150_000))));
        }
        all.sort(STATEMENT_ORDER);
        return List.copyOf(all);
    }
}
