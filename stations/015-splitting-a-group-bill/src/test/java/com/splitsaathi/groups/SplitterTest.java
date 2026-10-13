package com.splitsaathi.groups;

import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;

import static org.assertj.core.api.Assertions.assertThat;

/** The money rules on their own: parts always add up, and settle-up always clears every balance. */
class SplitterTest {

    @Test
    void sharesUseTheLargestRemainder() {
        Map<String, Integer> shares = new LinkedHashMap<>();
        shares.put("a", 1);
        shares.put("b", 1);
        shares.put("c", 1);
        assertThat(Splitter.shares(10_000, shares).values()).containsExactly(3_334L, 3_333L, 3_333L);
        shares.put("c", 2);  // 1:1:2 of 101 paise -> 25.25, 25.25, 50.5: the half paisa goes to c
        assertThat(Splitter.shares(101, shares).values()).containsExactly(25L, 25L, 51L);
    }

    @Test
    void aThousandRandomSplitsAllAddUpExactly() {
        Random random = new Random(42); // fixed seed: the same 1,000 cases every run
        for (int i = 0; i < 1_000; i++) {
            long total = 1 + random.nextInt(10_000_000);
            int people = 1 + random.nextInt(12);
            List<String> names = new ArrayList<>();
            Map<String, Integer> shares = new LinkedHashMap<>();
            for (int p = 0; p < people; p++) {
                names.add("p" + p);
                shares.put("p" + p, 1 + random.nextInt(5));
            }
            Map<String, Long> equal = Splitter.equal(total, names);
            assertThat(equal.values().stream().mapToLong(Long::longValue).sum()).isEqualTo(total);
            assertThat(equal.values().stream().mapToLong(Long::longValue).max().orElseThrow()
                    - equal.values().stream().mapToLong(Long::longValue).min().orElseThrow()).isLessThanOrEqualTo(1);
            assertThat(Splitter.shares(total, shares).values().stream().mapToLong(Long::longValue).sum()).isEqualTo(total);
        }
    }

    @Test
    void settleUpClearsEveryBalanceInAtMostNMinusOnePayments() {
        Map<String, Long> balances = new LinkedHashMap<>();
        balances.put("asha", 50_000L);
        balances.put("kabir", -20_000L);
        balances.put("meera", -10_000L);
        balances.put("ravi", -20_000L);
        var payments = SettleUp.payments(balances);
        assertThat(payments).hasSizeLessThanOrEqualTo(3);
        Map<String, Long> after = new LinkedHashMap<>(balances);
        payments.forEach(p -> {
            after.merge(p.from(), p.amountPaise(), Long::sum);
            after.merge(p.to(), -p.amountPaise(), Long::sum);
        });
        assertThat(after.values()).containsOnly(0L);
    }
}
